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
args = parser.parse_args()
print(json.dumps(
    CreatorSceneProduction(ROOT).produce_ready_episodes(
        args.episode_limit, args.batch_size, args.max_scenes
    ),
    ensure_ascii=False,
    indent=2,
))
