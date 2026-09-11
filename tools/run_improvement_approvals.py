"""Read owner Telegram improvement-review button decisions."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.improvement_review import ImprovementReview
from brain.memory import MemoryEngine
from tools.telegram import get_telegram_updates

if __name__ == "__main__":
    memory = MemoryEngine(os.getenv("AION_MEMORY_ROOT", "memory"))
    offsets = memory.all("telegram_improvement_offsets")
    values = []
    for entry in offsets:
        try:
            values.append(int(entry.get("content") or 0))
        except (TypeError, ValueError):
            continue
    updates = get_telegram_updates(offset=max(values, default=None))
    results = ImprovementReview(memory).handle_updates_once(updates)
    ids = [int(item["update_id"]) for item in updates if str(item.get("update_id", "")).isdigit()]
    if ids:
        memory.remember("telegram_improvement_offsets", str(max(ids) + 1), memory_type="observation",
                        source="aion-improvement-review", importance=1)
    print(json.dumps(results, ensure_ascii=False, default=str))
