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

    def snapshot(self, now=None):
        now = now or datetime.now(timezone.utc)
        stale = self._stale_authorizations(now)
        fallback = self._fallback_rate()
        recovery = self._recovery_catalogue()

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
            },
        }
