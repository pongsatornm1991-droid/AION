"""Bounded recovery plan for a missing Creator release buffer.

It never reuses an old reel, publishes, changes credentials, or generates an
unbounded backlog. The planner mirrors the Shorts-first 144-hour appointments,
prepares the next research-grounded storyboard when available, and leaves
media generation to the existing bounded Studio shift.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.release_readiness import ReleaseReadiness
from brain.research_to_story import ResearchToStory
from brain.research_story_handoff import ResearchStoryHandoff
from brain.story_episode_stager import StoryEpisodeStager
from brain.creator_series import CreatorSeriesRegistry
from brain.visual_story_policy import VisualStoryPolicy


def _active_by_kind(root):
    active = {"short": []}
    for item in CreatorSeriesRegistry(root).episodes():
        if item.get("pacing_policy") != VisualStoryPolicy.VERSION:
            continue
        if item.get("status") not in {"storyboard-ready-needs-assets", "assets-ready-for-assembly"}:
            continue
        kind = "short" if item.get("format") == "illustrated-narrated-short" else "archived-long-form"
        active.setdefault(kind, []).append(item.get("id"))
    return active


def recover_once(memory, root=ROOT):
    readiness = ReleaseReadiness(memory, root).snapshot()
    shortages = {
        item.get("content_kind"): int(item.get("missing") or 0)
        for item in (readiness.get("shortages") or [])
    }
    if not any(shortages.values()):
        return {"stage": "buffer-already-ready", "needs_production": False, "readiness": readiness}

    active = _active_by_kind(root)
    planned = {
        kind: max(0, shortages.get(kind, 0) - len(active.get(kind, [])))
        for kind in ("short",)
    }
    prepared = []
    # One run may prepare the next missing appointment.  The 3-hour Story
    # shift keeps filling the remaining plan without a user needing to order
    # it.  Deliberately do not fabricate three episodes from one weak source
    # package or start paid media generation in this observer.
    next_kind = next((kind for kind in ("short",) if planned[kind]), None)
    if next_kind:
        brief = ResearchToStory(memory).propose_once()
        handoff = ResearchStoryHandoff(memory).create_once()
        staged = StoryEpisodeStager(memory, root).stage_once(next_kind)
        prepared.append({"content_kind": next_kind, "brief": brief, "handoff": handoff, "staged": staged})
    else:
        staged = None

    return {
        "stage": "recovery-storyboard-prepared" if staged and staged.get("stage") in {"storyboard-staged", "already-staged"} else "recovery-needs-research",
        "needs_production": bool(staged and staged.get("stage") in {"storyboard-staged", "already-staged"}),
        "shortages": shortages,
        "active_pipeline": active,
        "remaining_storyboard_plan": planned,
        "prepared": prepared,
        "detail": "แผนนี้สร้างเฉพาะงานใหม่จากหลักฐาน และไม่ใช้คลิปเก่าเป็นตัวแทนของรอบที่ขาด",
    }


def main():
    # GitHub runners use UTF-8, while a local Windows console can default to
    # cp1252.  Recovery reports contain Thai operational detail, so ensure a
    # successful storyboard handoff is never misreported as a failed run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-root", default=os.getenv("AION_MEMORY_ROOT", "memory"))
    args = parser.parse_args()
    print(json.dumps(recover_once(MemoryEngine(args.memory_root)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
