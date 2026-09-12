import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from brain.creator_scene_production import CreatorSceneProduction

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=3)
args = parser.parse_args()
print(json.dumps(CreatorSceneProduction(ROOT).produce_once(args.limit), ensure_ascii=False, indent=2))
