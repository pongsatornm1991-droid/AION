"""Build auditable costume handoffs from AION Creator storyboards."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain.costume_direction import CostumeDirection
from brain.creator_series import CreatorSeriesRegistry


def build(output=None):
    briefs = []
    for episode in CreatorSeriesRegistry(ROOT).episodes():
        brief = CostumeDirection.episode_brief(episode)
        brief["quality"] = CostumeDirection.validate(brief)
        briefs.append(brief)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "department": CostumeDirection.DEPARTMENT,
        "status": "operational" if briefs and all(item["quality"]["eligible"] for item in briefs) else "needs-attention",
        "briefs": briefs,
    }
    target = Path(output or ROOT / "public" / "aion-costume-briefs.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
