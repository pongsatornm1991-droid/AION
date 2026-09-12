"""Write a public-safe defensive audit report for AION Cyber Guard."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.cyber_guard import CyberGuard

report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **CyberGuard(ROOT).snapshot()}
target = ROOT / "public" / "aion-cyber-guard.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
