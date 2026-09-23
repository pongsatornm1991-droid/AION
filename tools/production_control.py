"""Write a read-only public production-control report for the dashboard."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.production_control import ProductionControl


def main():
    report = ProductionControl(ROOT).snapshot()
    path = ROOT / "public" / "aion-production-control.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"state": report["state"], "path": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
