"""Post Thai-audio versions of already-published Shorts to the Facebook Page.

Owner, 2026-10-04: Facebook should be a Thai-first channel, and the Thai dubs
that already exist should not sit unused. Facebook has no multi-language audio
track (YouTube's dub audio has to be added by hand in Studio), so a Thai
version is a separate Reel: the episode's own finished video with its
scene-timed Thai narration (content/reels_thai/*.mp3, made by ThaiDubCycle)
laid over it.

Cost: none beyond ffmpeg time. The Thai audio already exists (edge-tts, free),
the video already exists, and the Graph API call is free -- no OpenAI credit
is spent. The video is rendered inside the run and never committed.

Safety/bounds:
  * only an episode whose YouTube Short is public AND whose Thai dub record
    exists is eligible, and its source video must still pass VideoQualityGate;
  * newest first, a small batch per run (never a flood of old posts);
  * each episode is recorded in `thai_facebook_crossposts`, so it is posted at
    most once; a failure is retried a few times, then left alone.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from brain.identity_disclosure import append_identity_disclosure
from brain.video_quality import VideoQualityGate

CATEGORY = "thai_facebook_crossposts"
DUB_CATEGORY = "youtube_thai_dubs"
MAX_ATTEMPTS = 3
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _ffmpeg():
    return shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def _duration(ffmpeg, path):
    from tools.reel_render import _audio_duration

    return _audio_duration(ffmpeg, path)


def mux_thai_audio(video_path, audio_path, output_path, ffmpeg=None, duration_reader=None, runner=None):
    """Replace a video's audio with the Thai track, keeping the whole video.

    Thai audio shorter than the video is padded with silence (video copied
    untouched); longer audio holds the last frame until it finishes (the
    video is re-encoded for that case only). Never speeds up or cuts speech.
    """
    ffmpeg = ffmpeg or _ffmpeg()
    read = duration_reader or (lambda path: _duration(ffmpeg, path))
    run = runner or (lambda cmd: subprocess.run(
        cmd, check=True, capture_output=True, text=True, timeout=600, creationflags=_NO_WINDOW))
    video_seconds, audio_seconds = read(video_path), read(audio_path)
    if not video_seconds or not audio_seconds:
        raise RuntimeError("could not read the video or Thai audio duration")
    base = [ffmpeg, "-y", "-i", str(video_path), "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0"]
    if audio_seconds <= video_seconds + 0.05:
        command = base + [
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-af", f"apad=whole_dur={video_seconds:.3f}", "-t", f"{video_seconds:.3f}",
            "-movflags", "+faststart", str(output_path),
        ]
        total = video_seconds
    else:
        extra = audio_seconds - video_seconds + 0.2
        command = base + [
            "-vf", f"tpad=stop_mode=clone:stop_duration={extra:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{audio_seconds + 0.2:.3f}",
            "-movflags", "+faststart", str(output_path),
        ]
        total = audio_seconds + 0.2
    run(command)
    return {"video_seconds": video_seconds, "audio_seconds": audio_seconds, "output_seconds": total,
            "reencoded": audio_seconds > video_seconds + 0.05}


class ThaiFacebookCrosspost:
    def __init__(self, memory, root):
        self.memory = memory
        self.root = Path(root)

    def _records(self, category):
        for entry in self.memory.all(category):
            try:
                payload = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if isinstance(payload, dict):
                yield entry, payload

    def _crosspost_record(self, episode_id):
        for entry, payload in self._records(CATEGORY):
            if payload.get("episode_id") == episode_id:
                return entry, payload
        return None, None

    def candidates(self):
        """Dubbed, public episodes still owed a Thai Facebook Reel, newest first."""
        dubs = [payload for _, payload in self._records(DUB_CATEGORY)
                if payload.get("episode_id") and payload.get("audio_path") and payload.get("title_th")]
        dubs.sort(key=lambda payload: str(payload.get("generated_at") or ""), reverse=True)
        pending, seen = [], set()
        for dub in dubs:
            episode_id = dub["episode_id"]
            if episode_id in seen:
                continue
            seen.add(episode_id)
            _, record = self._crosspost_record(episode_id)
            if record and (record.get("status") == "published" or int(record.get("attempts") or 0) >= MAX_ATTEMPTS):
                continue
            pending.append(dub)
        return pending

    @staticmethod
    def caption(dub):
        """A short Thai Facebook caption: title, link to the full video, hashtags.

        The YouTube description's middle paragraphs (a generic audience promise
        and a "state what the sources have not confirmed" boundary line) read
        like instructions on a Facebook post, so only the title, the link back
        and the hashtag line are carried over.
        """
        description = str(dub.get("description_th") or "")
        hashtags = next((line.strip() for line in reversed(description.splitlines()) if line.strip().startswith("#")), "")
        parts = [str(dub.get("title_th") or "").strip()]
        if dub.get("video_id"):
            parts.append(f"ดูฉบับเต็มบน YouTube: https://www.youtube.com/shorts/{dub['video_id']}")
        if hashtags:
            parts.append(hashtags)
        return append_identity_disclosure("\n\n".join(part for part in parts if part), "facebook")

    def publish_once(self, facebook_publisher=None, muxer=None, dry_run=False):
        pending = self.candidates()
        for dub in pending:
            episode_id = dub["episode_id"]
            video = self.root / "content" / "reels" / f"{episode_id}.mp4"
            audio = self.root / str(dub["audio_path"])
            if not video.is_file() or not audio.is_file():
                continue
            if not VideoQualityGate(self.root).assess(video, "short").get("eligible"):
                continue
            if dry_run:
                return {"stage": "would-publish", "episode_id": episode_id, "caption": self.caption(dub)}
            return self._publish(dub, video, audio, facebook_publisher, muxer)
        return {"stage": "nothing-to-publish", "waiting": len(pending)}

    def _publish(self, dub, video, audio, facebook_publisher, muxer):
        episode_id = dub["episode_id"]
        entry, record = self._crosspost_record(episode_id)
        record = record or {"episode_id": episode_id, "video_id": dub.get("video_id"), "attempts": 0}
        record["attempts"] = int(record.get("attempts") or 0) + 1
        record["last_attempt"] = datetime.now(timezone.utc).isoformat()
        try:
            with tempfile.TemporaryDirectory(prefix="aion-thai-fb-") as workdir:
                output = Path(workdir) / f"{episode_id}-thai.mp4"
                record["render"] = (muxer or mux_thai_audio)(video, audio, output)
                if facebook_publisher is None:
                    from tools.facebook import publish_reel_to_facebook
                    facebook_publisher = publish_reel_to_facebook
                record["result"] = facebook_publisher(str(output), caption=self.caption(dub))
            record["status"] = "published"
            record.pop("error", None)
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = (str(exc).strip() or type(exc).__name__)[:300]
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if entry is None:
            self.memory.remember(
                CATEGORY, payload, memory_type="action", source="aion-thai-facebook-crosspost",
                importance=3, tags=["facebook", "thai", "crosspost", episode_id],
            )
        else:
            self.memory.update(CATEGORY, entry["id"], content=payload)
        return {"stage": "published" if record["status"] == "published" else "failed",
                "episode_id": episode_id, "attempts": record["attempts"], "error": record.get("error")}

    def publish_batch(self, limit=1, **kwargs):
        results = []
        for _ in range(max(1, int(limit))):
            result = self.publish_once(**kwargs)
            results.append(result)
            if result.get("stage") != "published" or kwargs.get("dry_run"):
                break
        return {"stage": results[-1]["stage"], "results": results}
