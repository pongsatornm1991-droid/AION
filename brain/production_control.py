"""Truthful production observability for AION's automatic Shorts lane."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from brain.channel_policy import ChannelPolicy
from brain.youtube_creator_queue import YouTubeCreatorQueue
from brain.platform_preflight import PlatformPreflight
from brain.research_portfolio import ResearchPortfolio
from brain.memory import MemoryEngine
from brain.evidence_reserve import EvidenceReserve
from brain.system_integrity import SystemIntegrity


class VisualArtifactGate:
    """Check image files without pretending to understand their semantics."""

    MIN_VERTICAL = (720, 1280)

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _image(self, relative):
        path = self.root / str(relative or "")
        try:
            with Image.open(path) as image:
                width, height = image.size
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            vertical = width >= self.MIN_VERTICAL[0] and height >= self.MIN_VERTICAL[1] and abs(width / height - 9 / 16) <= 0.04
            return {"path": str(relative), "readable": True, "vertical": vertical, "digest": digest}
        except (OSError, ValueError):
            return {"path": str(relative), "readable": False, "vertical": False, "digest": None}

    def assess(self, episode):
        is_short = episode.get("format") == "illustrated-narrated-short"
        items = [self._image(scene.get("image")) for scene in episode.get("scenes") or []]
        reasons = []
        if not items:
            reasons.append("missing-scene-images")
        if any(not item["readable"] for item in items):
            reasons.append("missing-or-unreadable-scene-image")
        if is_short and any(not item["vertical"] for item in items):
            reasons.append("scene-image-not-vertical-9x16")
        digests = [item["digest"] for item in items if item["digest"]]
        if len(digests) != len(set(digests)):
            reasons.append("duplicate-scene-image")
        return {
            "eligible": not reasons,
            "reasons": reasons,
            "checked_scenes": len(items),
            "machine_check_only": True,
            "editorial_limit": "Checks actual files, dimensions and exact duplicates. It cannot truthfully detect text, anatomy, factual depiction or style compliance without a reviewed vision model.",
        }


class ProviderHealth:
    """Expose configuration truth; never invent provider quota or availability."""

    PRODUCTION_PLATFORMS = ("image", "video", "youtube", "facebook", "instagram")

    def __init__(self, environ=None):
        self.preflight = PlatformPreflight(environ)

    def snapshot(self):
        checks = [self.preflight.check(name) for name in self.PRODUCTION_PLATFORMS]
        blocked = [item["platform"] for item in checks if not item["configured"]]
        return {
            "state": "ready" if not blocked else "critical",
            "checks": checks,
            "blocked": blocked,
            "quota": "unknown-not-inspectable-without-provider-api",
            "boundary": "A configured key is not proof of live quota or provider uptime; the scheduled workflow records real provider failures separately.",
        }


class ProductionControl:
    """One read-only report for production, release and monitoring decisions."""

    ARTIFACT_MAX_AGE_SECONDS = 2 * 60 * 60

    def __init__(self, root=None, environ=None, memory_root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.policy = ChannelPolicy(self.root)
        self.environ = environ
        supplied_environment = environ if environ is not None else os.environ
        self.memory_root = Path(memory_root or supplied_environment.get("AION_MEMORY_ROOT") or (self.root / "memory"))

    def _published_episode_ids(self):
        """Return only Studio episodes with a durable public YouTube record.

        The creator-series JSON is a production artifact, so its historical
        ``production-ready-assets-and-script`` status is intentionally never
        mutated by the uploader.  The private Creator queue is the durable
        publication ledger.  Reading both here prevents a genuinely
        published episode from looking like it is still waiting in Studio --
        the exact dashboard error the owner caught on 2026-10-02.

        This is deliberately ID-based, never title-based: a title can change
        or recur, whereas a recorded public video ID attached to one episode
        is unambiguous.  If memory is unavailable, return an empty set rather
        than guessing that something was published.
        """
        try:
            records = YouTubeCreatorQueue(MemoryEngine(self.memory_root), self.root)._records_by_episode()
            return {
                str(episode_id)
                for episode_id, (_entry, payload) in records.items()
                if str((payload.get("youtube") or {}).get("video_id") or "").strip()
                and str((payload.get("youtube") or {}).get("privacy_status") or "").lower() == "public"
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return set()

    def _episodes(self, publish_ready_ids=None, published_ids=None):
        """Report Studio assets separately from the durable publish queue.

        A rendered episode is useful progress, but it is not a promise that
        a new Short can occupy a release slot.  That promise belongs to the
        private Creator queue after its final Quality Gate.  Keeping the two
        states separate prevents the dashboard from reporting an already
        published (or merely assembled) episode as a future release.
        """
        publish_ready_ids = publish_ready_ids or set()
        published_ids = published_ids or set()
        result = []
        gate = VisualArtifactGate(self.root)
        for path in sorted((self.root / "content" / "creator_series").glob("*.json")):
            try:
                episode = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            visual = gate.assess(episode)
            style = (episode.get("visual_style") or {}).get("id")
            ready = episode.get("status") == "production-ready-assets-and-script"
            published = str(episode.get("id") or "") in published_ids
            blockers = [] if published else list(visual["reasons"])
            if not published and style != self.policy.production()["automatic_release_visual_style"]:
                blockers.append("visual-style-not-channel-signature")
            if not published and not ready:
                blockers.append(f"episode-status:{episode.get('status') or 'unknown'}")
            result.append({
                "id": episode.get("id"), "title": episode.get("title"),
                "status": "published" if published else episode.get("status"),
                "source_status": episode.get("status"),
                "style": style, "scene_count": len(episode.get("scenes") or []),
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "visual_qa": visual, "studio_blockers": blockers,
                # Compatibility alias for older dashboard readers.  New
                # code should use studio_blockers: this is not the final
                # Creator release queue.
                "release_blockers": blockers,
                "studio_ready": not published and not blockers,
                "release_ready": not published and episode.get("id") in publish_ready_ids,
                "portfolio": ResearchPortfolio.assign(episode.get("topic_key") or episode.get("title")),
            })
        return result

    def _artifact_freshness(self, now):
        path = self.root / "public" / "aion-release-readiness.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(str(payload.get("generated_at")).replace("Z", "+00:00"))
            age = max(0, int((now - generated.astimezone(timezone.utc)).total_seconds()))
            current = int(payload.get("horizon_hours") or 0) == int(self.policy.publishing()["readiness_horizon_hours"])
            return {"state": "fresh" if current and age <= self.ARTIFACT_MAX_AGE_SECONDS else "stale", "age_seconds": age, "policy_current": current}
        except (OSError, ValueError, TypeError):
            return {"state": "missing", "age_seconds": None, "policy_current": False}

    def _release_readiness(self, now):
        """Read the one public report that is allowed to call work publish-ready."""
        path = self.root / "public" / "aion-release-readiness.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(str(payload.get("generated_at")).replace("Z", "+00:00"))
            age = max(0, int((now - generated.astimezone(timezone.utc)).total_seconds()))
            policy_current = int(payload.get("horizon_hours") or 0) == int(self.policy.publishing()["readiness_horizon_hours"])
            fresh = policy_current and age <= self.ARTIFACT_MAX_AGE_SECONDS
            buffer = payload.get("shorts_buffer") or {}
            available = (payload.get("available") or {}).get("short") or []
            ready = int(buffer.get("quality_ready") or 0)
            return {
                "state": "fresh" if fresh else "stale",
                "publish_ready": ready if fresh else None,
                "publish_ready_ids": {str(item) for item in available} if fresh else set(),
                "source_generated_at": payload.get("generated_at"),
                "age_seconds": age,
                "detail": buffer.get("detail") or "Counts only new Shorts that passed the final Quality Gate.",
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {
                "state": "missing", "publish_ready": None, "publish_ready_ids": set(),
                "source_generated_at": None, "age_seconds": None,
                "detail": "The final release queue has not reported yet; publish readiness is unknown.",
            }

    @staticmethod
    def _recovery(episodes, target, publish_ready, evidence_reserve=None):
        studio_ready = [item for item in episodes if item["studio_ready"]]
        active = [item for item in episodes if item.get("status") in {"storyboard-ready-needs-assets", "assets-ready-for-assembly"}]
        missing = max(0, target - publish_ready) if publish_ready is not None else target
        sla = (evidence_reserve or {}).get("recovery_sla") or {}
        next_steps = (
            ["Keep the fourteen qualified Shorts ready for release."] if not missing else
            ["Create distinct evidence-qualified story briefs.", "Stage up to five approved storyboards per recovery shift.", "Send staged Shorts to the bounded fourteen-episode Studio buffer.", "Publish only after image, assembly, and Quality Gates pass."]
        )
        if missing and not sla.get("fast_lane_active"):
            next_steps.insert(0, "Seed a distinct fast-lane mechanism topic before spending another deep-research attempt.")
        return {
            "owner": "Production Recovery Manager",
            "state": "maintaining" if not missing else "recovering",
            "target": target,
            "publish_ready": publish_ready,
            "studio_ready": len(studio_ready),
            "missing": missing,
            "active_storyboards": len(active),
            "cadence": "hourly while the buffer is below target",
            "next_steps": next_steps,
            "research_sla": sla,
        }

    def _evidence_reserve(self):
        """Read the private research inventory without inferring publication."""
        try:
            return EvidenceReserve(MemoryEngine(self.memory_root)).snapshot()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return {
                "state": "unknown",
                "targets": {},
                "counts": {},
                "next_action": "inspect the private evidence record",
                "boundary": "The evidence reserve could not be read; no readiness is inferred.",
                "error_type": type(exc).__name__,
            }

    def _integrity(self):
        """Cross-cutting checks a per-workflow green status cannot see.

        See brain/system_integrity.py's own docstring: an authorized episode
        that never reaches YouTube, a motion provider failing on every
        recent scene, or an exhausted recovery catalogue can each sit behind
        an individually "successful" workflow run for days. Folding this
        into the same report both surfaces it on the existing dashboard and
        lets a genuinely critical finding here escalate the overall state
        below, instead of needing a separate report nobody remembers to open.
        """
        try:
            return SystemIntegrity(MemoryEngine(self.memory_root), self.root).snapshot()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return {"state": "unknown", "alerts": [], "checks": {}, "error_type": type(exc).__name__}

    def snapshot(self, now=None):
        now = now or datetime.now(timezone.utc)
        target = self.policy.publishing()["shorts_buffer_target"]
        release = self._release_readiness(now)
        publish_ready = release["publish_ready"]
        published_ids = self._published_episode_ids()
        episodes = self._episodes(release["publish_ready_ids"], published_ids)
        studio_ready = [item for item in episodes if item["studio_ready"]]
        provider = ProviderHealth(self.environ).snapshot()
        freshness = self._artifact_freshness(now)
        evidence_reserve = self._evidence_reserve()
        integrity = self._integrity()
        states = {"provider": provider["state"], "artifact": freshness["state"], "integrity": integrity["state"]}
        state = (
            "critical" if provider["state"] != "ready" or integrity["state"] == "critical" else
            "critical" if publish_ready is not None and publish_ready <= 1 else
            "warning" if publish_ready is not None and publish_ready <= 3 else
            "attention" if publish_ready is None else
            "healthy" if publish_ready >= target and integrity["state"] == "healthy" else "attention"
        )
        return {
            "generated_at": now.isoformat(), "state": state, "policy": self.policy.load(),
            "shorts_buffer": {
                "target": target,
                "publish_ready": publish_ready,
                "studio_ready": len(studio_ready),
                "missing": max(0, target - publish_ready) if publish_ready is not None else None,
                "source": "aion-release-readiness.json" if release["state"] == "fresh" else "final-release-report-unavailable",
                "detail": release["detail"],
            },
            "episodes": episodes, "published_episode_ids": sorted(published_ids),
            "provider_health": provider, "release_artifact_freshness": freshness,
            "recovery": self._recovery(episodes, target, publish_ready, evidence_reserve), "evidence_reserve": evidence_reserve,
            "integrity": integrity,
            "portfolio": ResearchPortfolio.snapshot(), "component_states": states,
            "next_action": "produce new cited episodes through image, assembly and quality gates" if publish_ready is None or publish_ready < target else "maintain the fourteen-episode buffer",
        }
