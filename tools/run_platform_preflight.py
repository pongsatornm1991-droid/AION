"""Run a safe AION platform readiness check in CI without printing secrets."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.platform_preflight import PlatformPreflight


parser = argparse.ArgumentParser()
parser.add_argument("--require", choices=("image", "video", "youtube", "facebook", "instagram"))
args = parser.parse_args()
report = PlatformPreflight().check(args.require) if args.require else PlatformPreflight().snapshot()
print(json.dumps(report, ensure_ascii=False))
if args.require and not report["configured"]:
    raise SystemExit(2)
