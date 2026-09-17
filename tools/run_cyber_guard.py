"""Write a public-safe defensive audit report for AION Cyber Guard."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.cyber_guard import CyberGuard

# A defensive audit must not fail solely because a local terminal uses a
# legacy code page. GitHub Actions is UTF-8, but this keeps the same command
# inspectable and runnable on the chair's Windows workstation as well.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **CyberGuard(ROOT).snapshot()}
target = ROOT / "public" / "aion-cyber-guard.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
