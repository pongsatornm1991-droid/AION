"""Truthful production observability for AION's automatic Shorts lane."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from brain.channel_policy import ChannelPolicy
from brain.platform_preflight import PlatformPreflight
from brain.research_portfolio import ResearchPortfolio
from brain.memory import MemoryEngine
from brain.evidence_reserve import EvidenceReserve


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

    def _episodes(self):
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
            blockers = list(visual["reasons"])
            if style != self.policy.production()["automatic_release_visual_style"]:
                blockers.append("visual-style-not-channel-signature")
            if not ready:
                blockers.append(f"episode-status:{episode.get('status') or 'unknown'}")
            result.append({
                "id": episode.get("id"), "title": episode.get("title"), "status": episode.get("status"),
                "style": style, "scene_count": len(episode.get("scenes") or []),
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "visual_qa": visual, "release_blockers": blockers,
                "release_ready": not blockers,
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

    @staticmethod
    def _recovery(episodes, target):
        ready = [item for item in episodes if item["release_ready"]]
        active = [item for item in episodes if item.get("status") in {"storyboard-ready-needs-assets", "assets-ready-for-assembly"}]
        missing = max(0, target - len(ready))
        return {
            "owner": "Production Recovery Manager",
            "state": "maintaining" if not missing else "recovering",
            "target": target,
            "ready": len(ready),
            "missing": missing,
            "active_storyboards": len(active),
            "cadence": "hourly while the buffer is below target",
            "next_steps": (
                ["Keep the seven qualified Shorts ready for release."] if not missing else
                ["Create distinct evidence-qualified story briefs.", "Stage up to five approved storyboards per recovery shift.", "Send staged Shorts to the bounded seven-episode Studio shift.", "Publish only after image, assembly, and Quality Gates pass."]
            ),
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

    def snapshot(self, now=None):
        now = now or datetime.now(timezone.utc)
        episodes = self._episodes()
        target = self.policy.publishing()["shorts_buffer_target"]
        ready = [item for item in episodes if item["release_ready"]]
        provider = ProviderHealth(self.environ).snapshot()
        freshness = self._artifact_freshness(now)
        evidence_reserve = self._evidence_reserve()
        states = {"provider": provider["state"], "artifact": freshness["state"]}
        state = "critical" if provider["state"] != "ready" or len(ready) <= 1 else "warning" if len(ready) <= 3 else "healthy" if len(ready) >= target else "attention"
        return {
            "generated_at": now.isoformat(), "state": state, "policy": self.policy.load(),
            "shorts_buffer": {"target": target, "quality_ready": len(ready), "missing": max(0, target - len(ready))},
            "episodes": episodes, "provider_health": provider, "release_artifact_freshness": freshness,
            "recovery": self._recovery(episodes, target), "evidence_reserve": evidence_reserve,
            "portfolio": ResearchPortfolio.snapshot(), "component_states": states,
            "next_action": "produce new cited episodes through image, assembly and quality gates" if len(ready) < target else "maintain the seven-episode buffer",
        }
