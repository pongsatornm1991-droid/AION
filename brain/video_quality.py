"""Inspectable technical and frame-sampling checks for AION videos.

The gate deliberately distinguishes machine-verifiable checks from editorial
judgement.  It can reject a broken, silent, wrongly-shaped, black, or visually
static video.  It never pretends that this proves a story is interesting or
factually correct; those remain explicit Story and Evidence reviews.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageStat


class VideoQualityGate:
    """Run safe local checks before a video is offered for publication."""

    MIN_WIDTH = 720
    MIN_HEIGHT = 1280
    MIN_DURATION = 5.0
    MAX_DURATION = 180.0
    SAMPLE_COUNT = 3

    def __init__(self, root=None, runner=subprocess.run):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.runner = runner

    @staticmethod
    def _ffprobe_path():
        return shutil.which("ffprobe")

    @staticmethod
    def _ffmpeg_path():
        path = shutil.which("ffmpeg")
        if path:
            return path
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            return None

    def _probe(self, path):
        executable = self._ffprobe_path()
        try:
            if executable:
                result = self.runner(
                    [executable, "-v", "error", "-show_entries",
                     "format=duration:stream=codec_type,width,height",
                     "-of", "json", str(path)],
                    capture_output=True, text=True, check=False, timeout=20,
                )
                if not result.returncode:
                    return json.loads(result.stdout), None
            # imageio-ffmpeg commonly provides ffmpeg but not ffprobe.  Its
            # metadata output is sufficient for this deliberately small gate.
            ffmpeg = self._ffmpeg_path()
            if not ffmpeg:
                return None, "ffprobe-unavailable"
            result = self.runner(
                [ffmpeg, "-i", str(path), "-f", "null", "-"],
                capture_output=True, text=True, check=False, timeout=30,
            )
            text = f"{result.stdout}\n{result.stderr}"
            duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
            size_match = re.search(r"(\d{3,5})x(\d{3,5})", text)
            if not duration_match or not size_match:
                return None, "ffprobe-failed"
            hours, minutes, seconds = duration_match.groups()
            duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            streams = [{"codec_type": "video", "width": int(size_match.group(1)), "height": int(size_match.group(2))}]
            if re.search(r"Stream #\d+:\d+(?:\([^)]*\))?: Audio:", text):
                streams.append({"codec_type": "audio"})
            return {"format": {"duration": str(duration)}, "streams": streams}, None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None, "ffprobe-failed"

    @staticmethod
    def _frame_signature(path):
        with Image.open(path) as image:
            thumb = image.convert("L").resize((16, 16))
            stat = ImageStat.Stat(thumb)
            return round(stat.mean[0], 2), round(stat.var[0], 2), bytes(thumb.getdata())

    def _sample_frames(self, path, duration):
        executable = self._ffmpeg_path()
        if not executable:
            return [], "ffmpeg-unavailable"
        moments = [duration * fraction for fraction in (0.15, 0.5, 0.85)]
        samples = []
        try:
            with tempfile.TemporaryDirectory(prefix="aion-video-qa-") as temp:
                for index, moment in enumerate(moments):
                    output = Path(temp) / f"frame-{index}.jpg"
                    result = self.runner(
                        [executable, "-ss", f"{moment:.2f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", "-y", str(output)],
                        capture_output=True, text=True, check=False, timeout=30,
                    )
                    if result.returncode or not output.is_file():
                        continue
                    mean, variance, pixels = self._frame_signature(output)
                    samples.append({"mean_luma": mean, "variance": variance, "pixels": pixels})
        except (OSError, subprocess.SubprocessError, ValueError):
            return [], "frame-sampling-failed"
        return samples, None

    def assess(self, video_path):
        path = Path(video_path)
        if not path.is_absolute():
            path = self.root / path
        reasons = []
        if not path.is_file() or path.stat().st_size == 0:
            return {"eligible": False, "reasons": ["missing-or-empty-video"], "technical": {}, "frames": {}}

        probe, probe_error = self._probe(path)
        if probe_error:
            return {"eligible": False, "reasons": [probe_error], "technical": {}, "frames": {}}
        streams = probe.get("streams") or []
        video = next((item for item in streams if item.get("codec_type") == "video"), {})
        has_audio = any(item.get("codec_type") == "audio" for item in streams)
        try:
            duration = float((probe.get("format") or {}).get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0.0
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        ratio = (width / height) if height else 0
        if not video:
            reasons.append("missing-video-stream")
        if not has_audio:
            reasons.append("missing-audio-stream")
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            reasons.append("resolution-too-low")
        if ratio and abs(ratio - (9 / 16)) > 0.04:
            reasons.append("not-vertical-9x16")
        if not self.MIN_DURATION <= duration <= self.MAX_DURATION:
            reasons.append("duration-out-of-range")

        frames, frame_error = self._sample_frames(path, duration) if duration else ([], "no-duration")
        if frame_error:
            reasons.append(frame_error)
        elif len(frames) < self.SAMPLE_COUNT:
            reasons.append("insufficient-frame-samples")
        else:
            if any(item["mean_luma"] < 5 or item["variance"] < 2 for item in frames):
                reasons.append("black-or-nearly-static-frame")
            signatures = {item["pixels"] for item in frames}
            if len(signatures) == 1:
                reasons.append("all-sampled-frames-identical")

        return {
            "eligible": not reasons,
            "reasons": reasons,
            "technical": {"duration_seconds": round(duration, 2), "width": width, "height": height, "has_audio": has_audio},
            "frames": {"sampled": len(frames), "machine_check_only": True,
                       "editorial_limit": "Frame sampling cannot judge whether a story is engaging or whether AION is recognisable in every scene."},
        }
