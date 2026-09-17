"""Bounded recovery for a missing Creator release buffer.

It never reuses an old reel, publishes, changes credentials, or generates an
unbounded backlog.  When the 96-hour observer finds a missing Short, this
prepares at most one new research-grounded storyboard for the normal Studio
image/assembly workflows to complete.
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


def recover_once(memory, root=ROOT):
    readiness = ReleaseReadiness(memory, root).snapshot()
    missing_short = next(
        (item for item in readiness.get("shortages") or [] if item.get("content_kind") == "short"),
        None,
    )
    if not missing_short:
        return {"stage": "buffer-already-ready", "needs_production": False, "readiness": readiness}

    # A gap can already be on its way through images/assembly.  Starting a
    # second recovery topic each day would create the very duplicate queue
    # this tool is meant to prevent.
    active = [
        item for item in CreatorSeriesRegistry(root).episodes()
        if item.get("format") == "illustrated-narrated-short"
        and item.get("pacing_policy") == VisualStoryPolicy.VERSION
        and item.get("status") in {"storyboard-ready-needs-assets", "assets-ready-for-assembly"}
    ]
    if active:
        return {
            "stage": "recovery-already-in-production",
            "needs_production": False,
            "missing_short": missing_short.get("missing", 0),
            "episode_id": active[0].get("id"),
            "detail": "มีตอนใหม่กำลังผลิตอยู่แล้ว จึงไม่สร้างหัวข้อกู้บัฟเฟอร์ซ้ำ",
        }

    brief = ResearchToStory(memory).propose_once()
    handoff = ResearchStoryHandoff(memory).create_once()
    staged = StoryEpisodeStager(memory, root).stage_once()
    return {
        "stage": "recovery-storyboard-prepared" if staged.get("stage") in {"storyboard-staged", "already-staged"} else "recovery-needs-research",
        "needs_production": staged.get("stage") in {"storyboard-staged", "already-staged"},
        "missing_short": missing_short.get("missing", 0),
        "brief": brief,
        "handoff": handoff,
        "staged": staged,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-root", default=os.getenv("AION_MEMORY_ROOT", "memory"))
    args = parser.parse_args()
    print(json.dumps(recover_once(MemoryEngine(args.memory_root)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
