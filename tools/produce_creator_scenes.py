import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from brain.creator_scene_production import CreatorSceneProduction

parser = argparse.ArgumentParser()
parser.add_argument("--batch-size", type=int, default=25)
parser.add_argument("--max-scenes", type=int, default=120)
parser.add_argument("--episode-limit", type=int, default=1)
parser.add_argument("--format", choices=["short", "long-form"])
parser.add_argument("--require-complete", action="store_true",
                    help="Fail visibly when the planned release buffer could not be produced.")
args = parser.parse_args()
episode_format = {
    "short": "illustrated-narrated-short",
    "long-form": "long-form-illustrated",
}.get(args.format)
report = CreatorSceneProduction(ROOT).produce_ready_episodes(
    args.episode_limit, args.batch_size, args.max_scenes, episode_format
)
print(json.dumps(report, ensure_ascii=False, indent=2))
if args.require_complete and len(report.get("completed_episode_ids") or []) < args.episode_limit:
    raise SystemExit("planned-release-buffer-incomplete")
