"""Automatically prepare a Thai localization + dubbed narration track for
every newly published Creator episode.

Two-tier, matching what YouTube itself actually allows a third party to
automate (confirmed 2026-09-27 against YouTube's own API docs and multiple
independent developer guides):

- Title/description translation reaches the live video directly through the
  YouTube Data API's `localizations` field -- fully automatic, no manual
  step, and no separate "publish" action exists for it (the field has no
  draft/published status in its own schema).
- The dubbed *audio* track has no public API at all; YouTube Studio's own
  per-video Language tab is the only place to upload one. This cycle gets
  as close to done as code can: a finished, scene-timed Thai audio file
  saved into content/reels_thai/, ready for that one remaining upload click.

Never touches the evidence/research pipeline: this only rephrases an
episode's own already-approved English narration into Thai for dubbing,
never a new factual claim, and every translation is screened against
AION's existing claim-safety patterns (consciousness/emotion/subjective
experience) before being used for anything.
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from brain.evaluator import OutputEvaluator
from brain.youtube_creator_queue import YouTubeCreatorQueue

CATEGORY = "youtube_thai_dubs"
SOURCE_PREFIX = "aion-thai-dub:"

# Every other ffmpeg-invoking module (tools/reel_render.py, brain/video_quality.py,
# tools/produce_creator_motion.py) sets this so a console window doesn't flash for
# every subprocess call on Windows; matching that established pattern here.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
THAI_AUDIO_DIR = "content/reels_thai"

# Re-exported for existing call sites/tests; the check itself lives on
# OutputEvaluator so every module that needs it (Thai dubbing, the AI
# narration rewrite in story_episode_stager.py, ...) shares one definition.
has_unsafe_claim = OutputEvaluator.has_unsafe_claim


class ThaiDubCycle:
    def __init__(self, memory, root=None, provider=None, snippet_fn=None, localize_fn=None, tts_fn=None, ffmpeg_path=None):
        self.memory = memory
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.provider = provider
        if snippet_fn is None:
            from tools.youtube import get_video_snippet
            snippet_fn = get_video_snippet
        self.snippet_fn = snippet_fn
        if localize_fn is None:
            from tools.youtube import set_video_localization
            localize_fn = set_video_localization
        self.localize_fn = localize_fn
        if tts_fn is None:
            from tools.voice import synthesize_thai_voice
            tts_fn = synthesize_thai_voice
        self.tts_fn = tts_fn
        if ffmpeg_path is None:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        self.ffmpeg_path = ffmpeg_path

    # ------------------------------------------------------------------
    # Candidate selection
    # ------------------------------------------------------------------

    def _dubbed_episode_ids(self):
        return {
            entry["source"][len(SOURCE_PREFIX):]
            for entry in self.memory.all(CATEGORY)
            if str(entry.get("source") or "").startswith(SOURCE_PREFIX)
        }

    def _published_candidates(self):
        """Oldest-first published episodes with a real video id, not yet dubbed."""
        dubbed = self._dubbed_episode_ids()
        candidates = []
        for entry in self.memory.all(YouTubeCreatorQueue.CATEGORY):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            episode_id = payload.get("episode_id")
            youtube = payload.get("youtube") or {}
            video_id = str(youtube.get("video_id") or "").strip()
            if not episode_id or not video_id or episode_id in dubbed:
                continue
            if youtube.get("privacy_status") not in ("public", "unlisted"):
                continue
            candidates.append((str(entry.get("timestamp") or ""), episode_id, video_id))
        candidates.sort()
        return candidates

    def _episode_file(self, episode_id):
        path = self.root / "content" / "creator_series" / f"{episode_id}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _translate(self, title, description, narration_lines):
        prompt = "\n".join([
            "Translate the following AION video metadata and narration into natural, clear, spoken Thai suitable for narration/dubbing.",
            "Keep technical or proper terms understandable to a general audience.",
            "Never phrase anything as AION having feelings, consciousness, or subjective experience -- "
            "AION is an AI narrator describing evidence, never a sentient being.",
            "Return ONLY valid JSON with exactly this shape, no markdown fences, no extra commentary:",
            '{"title": "...", "description": "...", "narration": [%d strings, same order as given]}' % len(narration_lines),
            "",
            "TITLE:", str(title),
            "DESCRIPTION:", str(description),
            "NARRATION (in order):", json.dumps(narration_lines, ensure_ascii=False),
        ])
        raw = self.provider.generate(prompt).strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        if not isinstance(data, dict):
            raise ValueError("translation response was not a JSON object")
        if not isinstance(data.get("title"), str) or not isinstance(data.get("description"), str):
            raise ValueError("translation response is missing a title or description string")
        if len(data.get("narration") or []) != len(narration_lines):
            raise ValueError("translation returned a different number of narration lines than requested")
        return data

    # ------------------------------------------------------------------
    # Audio synthesis
    # ------------------------------------------------------------------

    @staticmethod
    def _atempo_chain(factor):
        """ffmpeg's atempo filter only accepts [0.5, 2.0] per stage -- chain
        stages for a factor outside that range.

        A zero or negative factor (e.g. from a zero-duration clip) would
        otherwise loop forever, since repeatedly dividing by 0.5 never
        reaches the loop's exit condition -- treated as 1.0 (no stretch)
        instead, since there is no sensible tempo change for a clip with no
        measurable duration.
        """
        if not factor or factor <= 0:
            factor = 1.0
        stages, remaining = [], factor
        while remaining < 0.5 or remaining > 2.0:
            step = 2.0 if remaining > 2.0 else 0.5
            stages.append(step)
            remaining /= step
        stages.append(remaining)
        return ",".join(f"atempo={value:.4f}" for value in stages)

    def _clip_duration(self, path):
        result = subprocess.run(
            [self.ffmpeg_path, "-i", str(path), "-f", "null", "-"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=_NO_WINDOW,
        )
        for line in result.stderr.splitlines():
            line = line.strip()
            if line.startswith("Duration:"):
                hours, minutes, seconds = line.split("Duration:")[1].split(",")[0].strip().split(":")
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        raise RuntimeError(f"Could not read audio duration for {path}")

    def _synthesize_track(self, narration_lines, scene_durations, output_path):
        """One continuous Thai audio file, each scene time-aligned to its
        original English scene duration so the dub stays in sync with the
        already-rendered visuals."""
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            stretched = []
            for index, (text, target) in enumerate(zip(narration_lines, scene_durations), start=1):
                raw_path = tmp / f"scene_{index:02d}_raw.mp3"
                if not self.tts_fn(text, str(raw_path)):
                    raise RuntimeError(f"Thai narration synthesis failed for scene {index}")
                raw_duration = self._clip_duration(raw_path)
                if raw_duration <= 0:
                    raise RuntimeError(f"Thai narration synthesis produced a zero-length clip for scene {index}")
                factor = (raw_duration / target) if target > 0 else 1.0
                stretched_path = tmp / f"scene_{index:02d}.mp3"
                subprocess.run(
                    [self.ffmpeg_path, "-y", "-i", str(raw_path), "-filter:a", self._atempo_chain(factor), str(stretched_path)],
                    check=True, capture_output=True, creationflags=_NO_WINDOW,
                )
                stretched.append(stretched_path)
            concat_list = tmp / "concat_list.txt"
            concat_list.write_text("\n".join(f"file '{path.name}'" for path in stretched), encoding="utf-8")
            subprocess.run(
                [self.ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(output_path)],
                check=True, capture_output=True, cwd=str(tmp), creationflags=_NO_WINDOW,
            )
        return self._clip_duration(output_path)

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def dub_once(self):
        candidates = self._published_candidates()
        if not candidates:
            return {"stage": "nothing-to-dub"}
        _, episode_id, video_id = candidates[0]

        episode = self._episode_file(episode_id)
        if episode is None:
            return {"stage": "episode-file-missing", "episode_id": episode_id}

        narration_lines = [str(scene.get("narration") or "") for scene in episode.get("scenes") or []]
        scene_durations = (episode.get("audio_visual_timeline") or {}).get("scene_durations") or []
        if not narration_lines or len(narration_lines) != len(scene_durations):
            return {"stage": "timing-data-missing", "episode_id": episode_id}

        try:
            live = self.snippet_fn(video_id)
        except Exception as exc:
            return {"stage": "snippet-fetch-failed", "episode_id": episode_id, "error": str(exc).strip() or type(exc).__name__}

        try:
            translated = self._translate(live["title"], live["description"], narration_lines)
        except Exception as exc:
            return {"stage": "translation-failed", "episode_id": episode_id, "error": str(exc).strip() or type(exc).__name__}

        unsafe_texts = [
            text for text in (translated["title"], translated["description"], *translated["narration"])
            if has_unsafe_claim(text)
        ]
        if unsafe_texts:
            return {"stage": "translation-blocked-claim-safety", "episode_id": episode_id, "unsafe_example": unsafe_texts[0]}

        try:
            self.localize_fn(video_id, "th", translated["title"], translated["description"])
        except Exception as exc:
            return {"stage": "localization-write-failed", "episode_id": episode_id, "error": str(exc).strip() or type(exc).__name__}

        audio_dir = self.root / THAI_AUDIO_DIR
        audio_dir.mkdir(parents=True, exist_ok=True)
        relative_audio_path = f"{THAI_AUDIO_DIR}/{episode_id}-thai.mp3"
        audio_path = self.root / relative_audio_path
        try:
            duration = self._synthesize_track(translated["narration"], scene_durations, audio_path)
        except Exception as exc:
            return {
                "stage": "audio-synthesis-failed", "episode_id": episode_id,
                # Title/description are already live at this point -- report
                # that honestly rather than implying the whole step failed.
                "localization_written": True,
                "error": str(exc).strip() or type(exc).__name__,
            }

        record = {
            "episode_id": episode_id, "video_id": video_id,
            "title_th": translated["title"], "description_th": translated["description"],
            "audio_path": relative_audio_path, "audio_duration_seconds": duration,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.remember(
            CATEGORY, json.dumps(record, ensure_ascii=False, sort_keys=True),
            memory_type="action", source=f"{SOURCE_PREFIX}{episode_id}", importance=3,
            tags=["youtube", "thai", "localization", episode_id],
        )
        return {"stage": "dubbed", **record}
