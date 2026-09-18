"""One evidence-backed control tower for AION's autonomous work.

This module deliberately does not publish, alter credentials, spend money, or
rewrite source code.  It joins records already produced by the real company
workflows so the Dashboard can state what is moving, what is waiting, and how
the normal recovery path will handle it.
"""

import json
from pathlib import Path

from brain.asset_hygiene import AssetHygiene
from brain.audience_accessibility import AudienceAccessibility
from brain.company_work_registry import CompanyWorkRegistry
from brain.delivery_watchdog import DeliveryWatchdog
from brain.system_reliability import SystemReliability
from brain.youtube_creator_queue import YouTubeCreatorQueue
from brain.continuity_guard import ContinuityGuard
from brain.work_queue import WorkQueue
from brain.platform_preflight import PlatformPreflight
from brain.studio_pipeline import StudioPipeline
from brain.release_readiness import ReleaseReadiness


class OperationsControlTower:
    """Read the company handoffs without creating a second source of truth."""

    PENDING = (
        ("pending_reels", "Reel", "รอรอบเผยแพร่หรือการส่งซ้ำที่ปลอดภัย"),
        ("pending_visual_content", "ภาพ Instagram", "รอรอบเผยแพร่หรือการส่งซ้ำที่ปลอดภัย"),
    )

    def __init__(self, memory, root=None):
        self.memory = memory
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _entries(self, category):
        try:
            return self.memory.all(category)
        except (OSError, ValueError, TypeError):
            return []

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "")
        except (AttributeError, TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def _pending_work(self):
        work = []
        for category, label, recovery in self.PENDING:
            entries = self._entries(category)
            if not entries:
                continue
            newest = max(entries, key=lambda item: item.get("timestamp", ""))
            payload = self._payload(newest)
            work.append({
                "lane": "เผยแพร่",
                "name": label,
                "state": "waiting",
                "count": len(entries),
                "detail": payload.get("caption") or recovery,
                "recovery": recovery,
                "timestamp": newest.get("timestamp"),
            })

        try:
            candidates = YouTubeCreatorQueue(self.memory, root=self.root).candidates()
        except (OSError, ValueError, TypeError):
            candidates = []
        for item in candidates:
            status = item.get("publication_status") or item.get("status")
            if status in {"published", "uploaded"} or str(status).startswith("retired"):
                continue
            # Historical drafts which failed a previous gate remain useful
            # audit evidence, but must not be displayed as today's blocked
            # release work.  The Story team will create a new, distinct
            # episode instead of reviving them as a fallback.
            if status in {"quality-blocked-story-and-audio", "quality-blocked"}:
                continue
            ready = status in {"authorized-for-aion-publish", "upload-ready"}
            work.append({
                "lane": "YouTube",
                "name": item.get("title") or "ตอน Creator ที่กำลังผลิต",
                "state": "active" if ready else "waiting",
                "count": 1,
                "detail": "ผ่าน Quality Gate พร้อมเข้ารอบเผยแพร่" if ready else "กำลังรอภาพ เสียง การประกอบ หรือ Quality Gate",
                "recovery": "YouTube Creator workflow จะตรวจคิวและเผยแพร่เฉพาะงานที่พร้อมตามรอบของแพลตฟอร์ม",
                "timestamp": item.get("updated_at") or item.get("created_at"),
            })
        return work

    def _creative_gate(self):
        """Expose pass/hold reasons, never an opaque creative score."""
        try:
            from brain.creator_series import CreatorSeriesRegistry
            episodes = CreatorSeriesRegistry(self.root).snapshot()
            return {
                "state": "pass",
                "label": "พร้อมตรวจตาม Quality Gate",
                "detail": f"ตรวจ storyboard {len(episodes)} ตอน: คุณค่าต่อผู้ชม, hook, แหล่งอ้างอิง, ขอบเขตความไม่แน่นอน, จังหวะฉาก และบทบาท AION",
                "episodes": len(episodes),
            }
        except (OSError, ValueError, TypeError) as exc:
            return {
                "state": "attention",
                "label": "ต้องแก้ storyboard ก่อนผลิตต่อ",
                "detail": str(exc),
                "episodes": 0,
            }

    def _preflight(self):
        """Make the existing production gates visible before external upload."""
        try:
            candidates = YouTubeCreatorQueue(self.memory, root=self.root).candidates()
        except (OSError, ValueError, TypeError):
            candidates = []
        items = []
        for item in candidates:
            if item.get("status") == "published":
                continue
            gate = item.get("quality_gate") or {}
            if item.get("status") == "retired":
                # Historic drafts are retained as audit evidence but must not
                # look like active work or a silent fallback for a release day.
                continue
            if item.get("release_blockers"):
                state, detail = "attention", "ยังไม่เข้าเกณฑ์รอบเผยแพร่: " + ", ".join(item["release_blockers"])
            elif not item.get("video_exists"):
                state, detail = "waiting", "รอประกอบวิดีโอจากภาพ เสียง และ storyboard"
            elif gate.get("eligible"):
                state, detail = "pass", "ผ่าน Quality Gate แล้ว รอรอบเผยแพร่"
            elif gate.get("state") == "blocked":
                state, detail = "attention", "Quality Gate ระบุสิ่งที่ต้องแก้ไว้แล้ว"
            else:
                state, detail = "waiting", "ก่อนอัปโหลดจะตรวจไฟล์, เสียง, สัดส่วน, ระยะเวลา, frame samples, คุณค่าต่อผู้ชม และงานซ้ำ"
            items.append({"title": item.get("title"), "state": state, "detail": detail, "reasons": gate.get("reasons") or []})
        return items

    def _audio_timing(self):
        """Audit source narration against storyboard time, including old renders."""
        try:
            from brain.creator_series import CreatorSeriesRegistry
            from brain.audio_visual_timing import AudioVisualTimingGate
            from brain.video_quality import VideoQualityGate
            from tools.reel_render import _audio_duration
            ffmpeg = VideoQualityGate._ffmpeg_path()
            episodes = CreatorSeriesRegistry(self.root).episodes()
        except (OSError, ValueError, TypeError):
            return []
        if not ffmpeg:
            return [{"state": "waiting", "detail": "เครื่องตรวจยังไม่มีตัวอ่านความยาวเสียง"}]
        reports = []
        for episode in episodes:
            audio = self.root / "content" / "reels" / f"{episode['id']}.mp3"
            if not audio.is_file():
                continue
            actual = _audio_duration(ffmpeg, audio)
            target = float(episode.get("target_duration_seconds") or 0)
            if actual is None or not target:
                continue
            timing = AudioVisualTimingGate.assess(actual, target)
            reports.append({
                "title": episode.get("title"),
                "state": "pass" if timing["eligible"] else "attention",
                "audio_seconds": round(actual, 2), "storyboard_seconds": target,
                "detail": timing["detail"],
                "next": "พร้อมให้ Video QA ตรวจไฟล์สุดท้าย" if timing["eligible"] else "ส่งกลับ Story และ Visual ก่อนประกอบไฟล์",
            })
        return reports

    def _self_repair(self):
        path = self.root / "public" / "aion-self-repair-status.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"state": "waiting", "label": "รอรอบตรวจซ่อมอัตโนมัติครั้งแรก", "detail": "Self-Repair Agent จะซ่อมเฉพาะรายการที่ขึ้นทะเบียนและตรวจสอบผลก่อนบันทึก"}
        return {
            "state": "pass" if payload.get("stage") in {"repaired", "checked-no-repair-needed"} else "attention",
            "label": "Self-Repair Agent ล่าสุด",
            "detail": f"{payload.get('stage')} · ซ่อม/กู้ได้ {payload.get('repaired_count', 0)} รายการ",
            "report": payload,
        }

    def _release_readiness(self):
        """Read the scheduled-release buffer published by its own watchdog."""
        path = self.root / "public" / "aion-release-readiness.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            # A local Dashboard must not report an artificial outage simply
            # because the committed GitHub artifact has not arrived yet.  It
            # can calculate the same read-only queue result from the synced
            # memory, while clearly labelling its source below.
            live = ReleaseReadiness(self.memory, self.root).snapshot()
            shortages = live.get("shortages") or []
            detail = "มีคลิปใหม่พร้อมสำหรับทุกช่วงเผยแพร่ 144 ชั่วโมงข้างหน้า" if not shortages else "ยังขาดบัฟเฟอร์: " + ", ".join(
                f"{item.get('content_kind')} {item.get('missing')} ตอน" for item in shortages
            )
            return {"state": live.get("state", "waiting"), "label": "บัฟเฟอร์วันเผยแพร่", "detail": detail, "report": live, "source": "local-live-queue"}
        # A committed report is useful evidence, but it must never override a
        # newer scheduling policy.  In particular, an older 96-hour artifact
        # made the Dashboard look like it was checking Sunday when it was not.
        # Recalculate read-only from the same queue until the publisher writes
        # a report using the current 144-hour policy.
        if payload.get("horizon_hours") != ReleaseReadiness.HORIZON_HOURS:
            live = ReleaseReadiness(self.memory, self.root).snapshot()
            shortages = live.get("shortages") or []
            detail = "มีคลิปใหม่พร้อมสำหรับทุกช่วงเผยแพร่ 144 ชั่วโมงข้างหน้า" if not shortages else "ยังขาดบัฟเฟอร์: " + ", ".join(
                f"{item.get('content_kind')} {item.get('missing')} ตอน" for item in shortages
            )
            return {
                "state": live.get("state", "waiting"),
                "label": "บัฟเฟอร์วันเผยแพร่",
                "detail": detail,
                "report": live,
                "source": "local-live-queue-policy-refresh",
                "stale_artifact": {
                    "generated_at": payload.get("generated_at"),
                    "horizon_hours": payload.get("horizon_hours"),
                },
            }
        shortages = payload.get("shortages") or []
        detail = "มีคลิปใหม่พร้อมสำหรับทุกช่วงเผยแพร่ 144 ชั่วโมงข้างหน้า" if not shortages else "ยังขาดบัฟเฟอร์: " + ", ".join(
            f"{item.get('content_kind')} {item.get('missing')} ตอน" for item in shortages
        )
        return {"state": payload.get("state", "waiting"), "label": "บัฟเฟอร์วันเผยแพร่", "detail": detail, "report": payload}

    def snapshot(self):
        pending = self._pending_work()
        delivery = DeliveryWatchdog(self.memory, root=self.root).snapshot()
        delivery_attention = [item for item in delivery["platforms"] if item["state"] != "verified"]
        reliability = SystemReliability(self.root).snapshot()
        assets = AssetHygiene(self.root, memory_root=getattr(self.memory, "root", None)).scan()["summary"]
        company = CompanyWorkRegistry(self.root).snapshot()
        workflow_attention = [item for item in company["departments"] if item["state"] in {"failure", "partial", "unknown"}]
        quality = self._creative_gate()
        audience = AudienceAccessibility(self.memory).snapshot()
        continuity = ContinuityGuard(self.root, getattr(self.memory, "root", None)).snapshot()
        self_repair = self._self_repair()
        release_readiness = self._release_readiness()
        work_queue = WorkQueue(self.memory).snapshot()
        studio_pipeline = StudioPipeline(self.root).snapshot()
        work_queue["active"] = list(studio_pipeline["active"]) + list(work_queue["active"])
        work_queue["total"] += studio_pipeline["total"]
        work_queue["active"].sort(key=lambda item: 0 if item.get("priority") == "urgent" else 1)
        preflight = PlatformPreflight().snapshot()

        # These two views intentionally never collapse into one status:
        # local preflight tells the owner what this private Dashboard machine
        # itself can do; GitHub workflow evidence tells whether the hosted
        # automation was able to do its job with its own sealed secrets.
        github_generated = company.get("generated_at")
        execution_context = {
            "local_observer": {
                "state": "read-only-observer",
                "label": "เครื่องนี้: ศูนย์สังเกตการณ์",
                "detail": "ไม่มีคีย์เผยแพร่ในเครื่องเป็นเรื่องปกติ; เครื่องนี้อ่านคิวและแสดงผลเท่านั้น",
                "preflight": preflight,
            },
            "github_automation": {
                "state": "reported" if github_generated else "waiting",
                "label": "GitHub: งานอัตโนมัติจริง",
                "detail": "อ่านผล GitHub Actions ล่าสุดที่เผยแพร่โดย workflow สุขภาพระบบ; ไม่แสดงข้อมูลรับรอง",
                "generated_at": github_generated,
                "source": company.get("source"),
                "departments": company.get("departments") or [],
            },
            "refresh": "หน้า Dashboard อ่านสถานะใหม่ทุก 15 วินาที; GitHub จะอัปเดตบันทึกทันทีหลังงานหลักจบ และมีรอบสำรองทุกชั่วโมง",
        }

        blockers = []
        for item in pending:
            if item["state"] == "waiting":
                blockers.append({"name": item["name"], "detail": item["recovery"], "state": "waiting"})
        for item in delivery_attention:
            blockers.append({"name": item["platform"].title(), "detail": "ยังไม่มีหลักฐานเผยแพร่ล่าสุด; Delivery Watchdog จะตรวจใหม่โดยไม่โพสต์ซ้ำ", "state": "attention"})
        for item in workflow_attention:
            blockers.append({"name": item["department"], "detail": "ต้องอาศัยผล workflow ล่าสุดก่อนยืนยันว่าการส่งต่องานครบ", "state": "attention"})
        if reliability["status"] != "healthy":
            blockers.append({"name": "โครงสร้างระบบ", "detail": reliability["scope"], "state": "attention"})
        if release_readiness["state"] != "ready":
            blockers.append({"name": release_readiness["label"], "detail": release_readiness["detail"], "state": release_readiness["state"]})

        return {
            "title": "AION Operations Control Tower",
            "purpose": "รวมคิวผลิต คุณภาพ การเผยแพร่ ผู้ชม และความน่าเชื่อถือจากหลักฐานจริง เพื่อให้งานไม่ค้างเงียบหรือทำซ้ำ",
            "status": "attention" if blockers or quality["state"] != "pass" else "healthy",
            "work_now": pending,
            "work_queue": work_queue,
            "platform_preflight": preflight,
            "execution_context": execution_context,
            "blockers": blockers,
            "quality_gate": quality,
            "preflight": self._preflight(),
            "audio_timing": self._audio_timing(),
            "delivery": delivery,
            "audience": audience,
            "asset_hygiene": assets,
            "continuity": continuity,
            "self_repair": self_repair,
            "release_readiness": release_readiness,
            "workflow_register": company,
            "recovery_policy": "งานที่รอจะถูกเก็บในคิวเดิมและลองใหม่โดย workflow ปกติ; ไม่สร้างโพสต์ซ้ำ ไม่ใช้ภาพเก่าแทน และไม่แตะสิทธิ์บัญชี เงิน หรือข้อมูลรับรอง",
        }
