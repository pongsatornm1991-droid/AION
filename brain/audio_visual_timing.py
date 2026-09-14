"""Pre-assembly timing gate for AION Studio narration and visuals.

The final MP4 can conceal a failure when a muxer trims an overlong narration.
This small, deterministic gate inspects the source narration against the
storyboard before final assembly, so Story and Visual receive a usable repair
brief rather than a silently cut ending.
"""

import math


class AudioVisualTimingGate:
    """Decide whether raw narration can fit the approved visual plan."""

    TOLERANCE_SECONDS = 0.25
    MAX_SCENE_SECONDS = 5

    @classmethod
    def assess(cls, audio_seconds, visual_seconds):
        """Return an inspectable pass/return-to-story decision.

        Audio and visual production may proceed in parallel after Story locks
        its timing plan.  Final assembly is allowed only when this gate passes.
        """
        try:
            audio = float(audio_seconds)
            visual = float(visual_seconds)
        except (TypeError, ValueError):
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["invalid-audio-or-storyboard-duration"],
                "detail": "อ่านความยาวเสียงหรือ storyboard ไม่ได้ จึงห้ามประกอบไฟล์สุดท้าย",
            }
        if audio <= 0 or visual <= 0:
            return {
                "eligible": False,
                "state": "return-to-story",
                "reasons": ["non-positive-audio-or-storyboard-duration"],
                "audio_seconds": round(audio, 2),
                "visual_seconds": round(visual, 2),
                "detail": "เสียงและ storyboard ต้องมีความยาวมากกว่า 0 วินาทีก่อนผลิต",
            }
        delta = audio - visual
        eligible = delta <= cls.TOLERANCE_SECONDS
        report = {
            "eligible": eligible,
            "state": "pass" if eligible else "return-to-story",
            "reasons": [] if eligible else ["audio-overruns-storyboard"],
            "audio_seconds": round(audio, 2),
            "visual_seconds": round(visual, 2),
            "delta_seconds": round(delta, 2),
        }
        if eligible:
            report["detail"] = "เสียงต้นฉบับอยู่ในเวลาที่ภาพรองรับ พร้อมประกอบไฟล์สุดท้าย"
        else:
            beats = math.ceil(delta / cls.MAX_SCENE_SECONDS)
            report["minimum_extra_visual_beats"] = beats
            report["detail"] = (
                f"เสียงยาวกว่าภาพ {delta:.2f} วินาที — ส่งกลับฝ่ายเรื่องเล่า: "
                f"ย่อบท หรือเพิ่มอย่างน้อย {beats} จังหวะภาพ (จังหวะละไม่เกิน 5 วินาที)"
            )
        return report
