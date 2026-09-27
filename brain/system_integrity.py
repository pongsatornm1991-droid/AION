"""Cross-cutting checks that surface a silently-masked pipeline failure.

Every individual workflow already reports its own success or failure. The
gap this module closes is different: on 2026-09-25, five separate real
faults (a registry crash, a metadata write-back bug, an exhausted recovery
catalogue, and an expired YouTube OAuth token that failed for at least five
days) each went unnoticed because nothing checked the *combination* of two
individually-green signals -- an episode can be "authorized" and the
workflow can report "success" while the actual upload silently failed.

This is deliberately read-only. It never authorizes, retries, or publishes
anything; it only names a condition that is worth a human or the next
session looking at.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry
from brain.curiosity import CuriosityEngine
from brain.initiative import AutonomousInitiative
from brain.research_to_story import ResearchToStory

ROOT = Path(__file__).resolve().parents[1]

FALLBACK_PROVIDERS = {"aion-static-fallback", "aion-kinetic-fallback"}


class SystemIntegrity:
    # An authorized episode should reach YouTube well within one daily
    # publishing cycle (currently every 24h). Twice that catches a missed
    # cron plus one recovery attempt without false-alarming on a slot that
    # simply hasn't come up yet.
    STALE_AUTHORIZATION_HOURS = 48
    FALLBACK_SAMPLE_EPISODES = 3
    RECOVERY_CATALOGUE_LOW = 5
    # research-to-story.yml runs every 3h; 24h is at least 8 missed cycles
    # in a row, well past anything a single delayed or skipped run explains.
    RESEARCH_STALL_HOURS = 24
    # A lone candidate can sit unconverted forever entirely by design (for
    # example a citation follow-up question about an already-published
    # video, which should never become a new episode) -- that must never
    # alone trip this alert permanently. The real 2026-09-27 stall showed
    # up as several distinct topics stuck at once, the same
    # minimum-sample-size guard FALLBACK_SAMPLE_EPISODES already uses below.
    RESEARCH_STALL_SAMPLE = 3

    def __init__(self, memory, root=None):
        self.memory = memory
        self.root = Path(root or ROOT)

    def _latest_queue_records(self):
        """The latest durable youtube_creator_queue record per episode.

        Mirrors YouTubeCreatorQueue._records_by_episode() without importing
        it, so this module stays a plain read-only observer of the same
        memory category rather than coupling to that class's internals.
        """
        records = {}
        for entry in self.memory.all("youtube_creator_queue"):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            episode_id = payload.get("episode_id")
            if episode_id:
                records[episode_id] = (entry, payload)
        return records

    def _stale_authorizations(self, now):
        stale = []
        for episode_id, (entry, payload) in self._latest_queue_records().items():
            if payload.get("upload_status") != "authorized-for-aion-publish":
                continue
            try:
                stamped = datetime.strptime(str(entry.get("timestamp")), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            age_hours = (now - stamped).total_seconds() / 3600
            if age_hours >= self.STALE_AUTHORIZATION_HOURS:
                stale.append({
                    "episode_id": episode_id,
                    "authorized_at": entry.get("timestamp"),
                    "age_hours": round(age_hours, 1),
                })
        return sorted(stale, key=lambda item: -item["age_hours"])

    def _fallback_rate(self):
        """Real-provider vs. fallback share across the most recently touched episodes.

        Only episodes that actually attempted motion (carry a
        motion_contract on at least one scene) count; a storyboard that
        simply hasn't reached that stage yet is not evidence of a fallback
        problem.
        """
        try:
            candidates = [
                path for path in (self.root / "content" / "creator_series").glob("*.json")
            ]
        except OSError:
            return {"sampled_episodes": 0, "sampled_scenes": 0, "fallback_scenes": 0, "rate": None}
        with_motion = []
        for path in candidates:
            try:
                episode = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            scenes = episode.get("scenes") or []
            if any(scene.get("motion_contract") for scene in scenes):
                with_motion.append((path.stat().st_mtime, episode))
        with_motion.sort(key=lambda item: -item[0])
        recent = [episode for _, episode in with_motion[: self.FALLBACK_SAMPLE_EPISODES]]
        sampled_scenes = 0
        fallback_scenes = 0
        for episode in recent:
            for scene in episode.get("scenes") or []:
                contract = scene.get("motion_contract")
                if not contract:
                    continue
                sampled_scenes += 1
                if contract.get("provider") in FALLBACK_PROVIDERS:
                    fallback_scenes += 1
        rate = (fallback_scenes / sampled_scenes) if sampled_scenes else None
        return {
            "sampled_episodes": len(recent),
            "sampled_scenes": sampled_scenes,
            "fallback_scenes": fallback_scenes,
            "rate": rate,
        }

    def _recovery_catalogue(self):
        try:
            initiative = AutonomousInitiative(self.memory, CuriosityEngine(self.memory))
            asked = initiative._asked_recovery_statements()
        except (OSError, ValueError, TypeError):
            return {"total": None, "remaining": None}
        total = len(AutonomousInitiative.RECOVERY_INQUIRIES)
        remaining = sum(
            1 for _, question, _ in AutonomousInitiative.RECOVERY_INQUIRIES
            if question.strip().lower() not in asked
        )
        return {"total": total, "remaining": remaining}

    def _research_pipeline_stall(self, now):
        """Evidence is qualified and waiting, but nothing new has progressed.

        Regression for 2026-09-27: a duplicate-topic false-positive in
        ContentNoveltyLedger silently blocked every waiting candidate for
        two days before the owner noticed and asked why nothing had
        published. _stale_authorizations only sees an episode that already
        reached "authorized-for-aion-publish" -- a novelty-gate block
        happens far earlier in the pipeline and left no trace there at
        all. This catches the same class of failure at the stage it
        actually occurs: real, evidence-qualified topics sitting
        unconverted while story_research_briefs goes quiet. Age is judged
        per candidate by its own most recently arrived evidence source
        (when the group actually became eligible) rather than by "no
        brief has ever existed," so a candidate that only just qualified
        never false-alarms before the next scheduled run even has a
        chance to pick it up.
        """
        rts = ResearchToStory(self.memory)
        briefs = rts._briefs()
        existing_roots = {str(item.get("root_question_id") or "") for item in briefs}
        try:
            pending = [item for item in rts.candidates() if item["root_question_id"] not in existing_roots]
        except (OSError, ValueError, TypeError, KeyError):
            return {"pending_candidates": None, "oldest_ready_hours": None}
        if not pending:
            return {"pending_candidates": 0, "oldest_ready_hours": None}
        ready_ages = []
        for item in pending:
            stamps = []
            for source in item.get("sources") or []:
                try:
                    stamped = datetime.strptime(str(source.get("timestamp")), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                stamps.append(stamped)
            if stamps:
                # the group became eligible once its last-arriving source landed
                ready_ages.append((now - max(stamps)).total_seconds() / 3600)
        return {
            "pending_candidates": len(pending),
            "oldest_ready_hours": round(max(ready_ages), 1) if ready_ages else None,
        }

    def snapshot(self, now=None):
        now = now or datetime.now(timezone.utc)
        stale = self._stale_authorizations(now)
        fallback = self._fallback_rate()
        recovery = self._recovery_catalogue()
        research_stall = self._research_pipeline_stall(now)

        alerts = []
        if stale:
            alerts.append({
                "check": "stale-authorization",
                "severity": "critical",
                "detail": (
                    f"{len(stale)} episode(s) authorized for {self.STALE_AUTHORIZATION_HOURS}h+ "
                    "without reaching YouTube -- the last time this happened it was a dead OAuth "
                    "token that silently failed for 5 days."
                ),
                "episodes": stale,
            })
        if fallback["rate"] == 1.0 and fallback["sampled_episodes"] >= self.FALLBACK_SAMPLE_EPISODES:
            alerts.append({
                "check": "motion-fallback-rate",
                "severity": "warning",
                "detail": (
                    f"the last {fallback['sampled_episodes']} episodes with motion attempts used "
                    "the still-hold fallback for every scene -- the real motion provider may be "
                    "unreachable, not just occasionally rejecting a scene."
                ),
                "fallback": fallback,
            })
        if recovery["remaining"] is not None and recovery["remaining"] <= self.RECOVERY_CATALOGUE_LOW:
            alerts.append({
                "check": "recovery-catalogue-low",
                "severity": "warning",
                "detail": (
                    f"only {recovery['remaining']} of {recovery['total']} recovery topics remain "
                    "unused -- the reserve will stop seeding new fast-lane questions once this "
                    "reaches zero, the same way it already did once."
                ),
                "recovery": recovery,
            })
        if (
            (research_stall["pending_candidates"] or 0) >= self.RESEARCH_STALL_SAMPLE
            and research_stall["oldest_ready_hours"] is not None
            and research_stall["oldest_ready_hours"] >= self.RESEARCH_STALL_HOURS
        ):
            alerts.append({
                "check": "research-pipeline-stall",
                "severity": "critical",
                "detail": (
                    f"{research_stall['pending_candidates']} evidence-qualified topic(s) have been "
                    f"ready for {research_stall['oldest_ready_hours']}h+ without becoming a story "
                    "brief -- the last time this happened, a duplicate-topic false-positive silently "
                    "blocked every candidate for two days before anyone noticed."
                ),
                "research_stall": research_stall,
            })

        state = (
            "critical" if any(item["severity"] == "critical" for item in alerts) else
            "attention" if alerts else
            "healthy"
        )
        return {
            "generated_at": now.isoformat(),
            "state": state,
            "alerts": alerts,
            "checks": {
                "stale_authorizations": stale,
                "motion_fallback": fallback,
                "recovery_catalogue": recovery,
                "research_pipeline_stall": research_stall,
            },
        }
