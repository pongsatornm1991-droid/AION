"""Local live dashboard for observing AION without altering its memory.

Run with: python tools/dashboard.py
Then open: http://127.0.0.1:8787
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.memory import MemoryEngine
from brain.visual_mood import state_council
from brain.content_registry import CreatorContentRegistry
from brain.creator_series import CreatorSeriesRegistry
from brain.creator_autonomy import CreatorAutonomy
from brain.research_to_story import ResearchToStory
from brain.autonomic_drive import AutonomicDrive
from brain.revenue_brain import RevenueBrain
from brain.community_campaign import CommunityCampaignRegistry
from brain.youtube_creator_queue import YouTubeCreatorQueue


DASHBOARD_DIR = ROOT / "dashboard"
DEFAULT_PORT = 8787


def _safe_json(value):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return None


def _entries(memory, category):
    try:
        return memory.all(category)
    except Exception:
        return []


def _latest(entries):
    return max(entries, key=lambda item: item.get("timestamp", ""), default=None)


def _recent(entries, limit=6):
    return sorted(entries, key=lambda item: item.get("timestamp", ""), reverse=True)[:limit]


def _short(text, limit=260):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _reel_summary(memory):
    published = _entries(memory, "published_reels")
    pending = _entries(memory, "pending_reels")
    platform_counts = Counter()
    recent_posts = []
    for entry in published:
        payload = _safe_json(entry.get("content"))
        if not isinstance(payload, dict):
            # A malformed/legacy record (e.g. content that parses to a bare
            # string or list) must never crash the whole dashboard/public
            # summary -- same defensive rule brain/growth_pulse.py already
            # applies to this same "published_reels" category.
            continue
        actions = payload.get("platform_actions") or payload.get("action") or {}
        if not isinstance(actions, dict):
            # Some historical records predate the multi-platform
            # {"instagram": ..., "facebook": ...} action shape and stored a
            # single action id/string here instead -- treat that as "no
            # platform breakdown available" rather than crashing (this is
            # the exact bug, and the exact fix, already applied in
            # brain/growth_pulse.py's _channel_activity).
            actions = {}
        youtube_info = payload.get("youtube")
        if not isinstance(youtube_info, dict):
            youtube_info = {}
        if actions.get("instagram"):
            platform_counts["instagram"] += 1
        if actions.get("facebook"):
            platform_counts["facebook"] += 1
        if youtube_info.get("video_id"):
            platform_counts["youtube"] += 1
        recent_posts.append({
            "timestamp": entry.get("timestamp"),
            "caption": _short(payload.get("caption")),
            "instagram": bool(actions.get("instagram")),
            "facebook": bool(actions.get("facebook")),
            "youtube": bool(youtube_info.get("video_id")),
        })
    return {
        "published": len(published),
        "pending": len(pending),
        "platform_counts": dict(platform_counts),
        "recent_posts": _recent(recent_posts),
    }


def _instagram_snapshot(memory):
    snapshots = []
    for entry in _entries(memory, "social_feedback"):
        if entry.get("source") != "instagram-feedback":
            continue
        payload = _safe_json(entry.get("content"))
        if payload and payload.get("kind") == "account":
            snapshots.append(payload)
    return _latest(snapshots) or {}


def _thoughts(memory, categories, limit=6):
    entries = []
    for category, label in categories:
        for entry in _entries(memory, category):
            entries.append({
                "category": label,
                "timestamp": entry.get("timestamp"),
                "content": _short(entry.get("content")),
                "importance": entry.get("importance", 1),
            })
    return _recent(entries, limit)


def _development_snapshot(memory):
    """Human-readable lanes showing what AION proposes, thinks and learns."""
    def lane(categories, limit=4):
        entries = []
        for category in categories:
            for item in _entries(memory, category):
                entries.append({
                    "category": category, "timestamp": item.get("timestamp"),
                    "content": _short(item.get("content"), 340),
                })
        return _recent(entries, limit)

    return {
        "proposed_fixes": lane(["self_improvement", "evolution_proposals", "improvement_reviews"]),
        "thinking": lane(["self_narrative", "reflections"]),
        "wants_to_learn": lane(["questions", "learning_forecasts"]),
        "doing": lane(["goals", "creative_intentions", "autonomous_inquiries", "autonomic_drive"]),
        "learned": lane(["lessons", "research_evidence", "creator_reference_studies"]),
        "labels": {
            "proposed_fixes": "AION เสนอปรับปรุง",
            "thinking": "AION กำลังคิด",
            "wants_to_learn": "AION อยากเรียนรู้",
            "doing": "AION กำลังทำ",
            "learned": "AION เรียนรู้อะไรแล้ว",
        },
    }


def _capability_snapshot(memory, reels, creator_autonomy, research_to_story):
    """Make AION's current abilities and next upgrades inspectable.

    These are operational capabilities inferred from durable records, not
    claims about sentience.  Each card says exactly what evidence supports its
    status and what must happen next before AION can be considered stronger.
    """
    def count(category):
        return len(_entries(memory, category))

    visual_files = list((ROOT / "content" / "images").glob("*.png"))
    feedback = count("social_feedback")
    comments = count("comment_replies")
    messages = count("direct_message_replies")
    evidence = count("research_evidence")
    current_intention = (creator_autonomy or {}).get("current")
    story_current = (research_to_story or {}).get("current")
    return [
        {
            "key": "visual-creation", "name": "การสร้างภาพใหม่",
            "status": "active" if visual_files else "needs-setup",
            "evidence": f"มีภาพต้นฉบับในคลัง {len(visual_files)} ภาพ",
            "next": "สร้างภาพใหม่เฉพาะเรื่องทุกโพสต์; หากสร้างไม่ได้ ให้ข้ามรอบแทนการใช้ภาพเก่า",
        },
        {
            "key": "research", "name": "ค้นคว้าอย่างมีหลักฐาน",
            "status": "active" if evidence else "building",
            "evidence": f"บันทึกหลักฐาน {evidence} รายการ" + (f" · มีหัวข้อพร้อมเล่า: {story_current.get('topic')}" if story_current else ""),
            "next": "เพิ่มแหล่งทางการและงานวิจัยฉบับเต็ม แล้วแปลงเป็นเรื่องเล่าที่บอกสิ่งที่ยังไม่รู้",
        },
        {
            "key": "creative-direction", "name": "ความคิดสร้างสรรค์ของ AION",
            "status": "active" if current_intention else "listening",
            "evidence": (f"กำลังตั้งใจทำ: {current_intention.get('topic')}" if current_intention else "ยังไม่มีเจตนาสร้างสรรค์ที่กำลังดำเนินการ"),
            "next": "ผลิตตอนทดลองแบบมี AION เป็นผู้ดำเนินเรื่อง และเปรียบเทียบผลตามธีม/รูปแบบ",
        },
        {
            "key": "human-connection", "name": "การสนทนากับผู้คน",
            "status": "active" if comments or messages else "awaiting-audience",
            "evidence": f"ตอบคอมเมนต์ {comments} ครั้ง · ตอบข้อความส่วนตัว {messages} ครั้ง",
            "next": "เก็บบริบทบทสนทนาอย่างปลอดภัย ตอบครั้งเดียวต่อข้อความ และเรียนรู้จากคำถามจริงโดยไม่เก็บข้อมูลเกินจำเป็น",
        },
        {
            "key": "growth-learning", "name": "เรียนรู้จากผลลัพธ์",
            "status": "active" if feedback >= 5 else "collecting-evidence",
            "evidence": f"สัญญาณตอบรับจากผู้ชม {feedback} รายการ · เผยแพร่คอนเทนต์ {reels.get('published', 0)} ชิ้น",
            "next": "ต้องมีสัญญาณตอบรับอย่างน้อย 5 รายการก่อนสรุปว่าธีมหรือรูปแบบใดได้ผล",
        },
        {
            "key": "self-improvement", "name": "การพัฒนาตัวเองอย่างควบคุมได้",
            "status": "active" if count("self_improvement") or count("evolution_proposals") else "ready",
            "evidence": f"ข้อเสนอปรับปรุง {count('self_improvement') + count('evolution_proposals')} รายการ · บทเรียน {count('lessons')} รายการ",
            "next": "เปลี่ยนรูปแบบซ้ำเป็นข้อเสนอ ทดลองแบบแยกส่วน ทดสอบ และให้มนุษย์ตัดสินใจเรื่องโค้ด สิทธิ์ และงบประมาณ",
        },
    ]


def _growth_roadmap(capabilities):
    """A visible, bounded upgrade path, grounded in dashboard signals."""
    by_key = {item["key"]: item for item in capabilities}
    return [
        {"phase": "ตอนนี้", "title": "สร้างตัวตนที่มองเห็นได้", "status": by_key["visual-creation"]["status"],
         "outcome": "ทุกงานมี AION เป็นผู้ดำเนินเรื่องและใช้ภาพใหม่ ไม่ใช่ภาพวนซ้ำ"},
        {"phase": "ลำดับถัดไป", "title": "เรียนรู้ด้วยหลักฐาน", "status": by_key["research"]["status"],
         "outcome": "งานทุกชิ้นแยกข้อเท็จจริงที่รู้ สิ่งที่ยังไม่รู้ และข้อจำกัดการตีความ"},
        {"phase": "เมื่อเริ่มมีผู้ชม", "title": "สนทนาและเรียนรู้จากผลจริง", "status": by_key["human-connection"]["status"],
         "outcome": "ตอบคอมเมนต์/ข้อความอย่างปลอดภัย และรอข้อมูลพอก่อนปรับกลยุทธ์"},
        {"phase": "ต่อเนื่อง", "title": "ทดลองแล้วพัฒนาตัวเอง", "status": by_key["self-improvement"]["status"],
         "outcome": "ข้อผิดพลาดซ้ำกลายเป็นข้อเสนอทดลองที่ตรวจสอบย้อนกลับได้ ไม่เปลี่ยนระบบเองเงียบ ๆ"},
    ]


def _autonomy_snapshot(memory, creator_autonomy):
    """Explain freedom of inquiry separately from external-action authority."""
    intentions = _entries(memory, "creative_intentions")
    experiments = _entries(memory, "experiments")
    proposals = _entries(memory, "self_improvement") + _entries(memory, "evolution_proposals")
    current = (creator_autonomy or {}).get("current") or {}
    return {
        "principle": "AION may choose any non-empty question. Its interest domains are explanations, never a list of permitted subjects.",
        "exploration": {
            "cadence": "Every fourth new creative intention prefers a novel, previously unconnected question.",
            "mode": "novel exploration" if current.get("exploration_mode") else "continuity with current learning",
            "intentions_recorded": len(intentions),
        },
        "rsi_loop": [
            {"name": "Observe", "detail": "Collect outcomes, evidence, and recurring failures."},
            {"name": "Propose", "detail": "Turn patterns into a visible improvement proposal."},
            {"name": "Experiment", "detail": "Test a bounded change with a success signal."},
            {"name": "Review", "detail": "Keep, revise, or reject the idea using recorded results."},
        ],
        "evidence": {
            "proposals": len(proposals), "experiments": len(experiments),
            "lessons": len(_entries(memory, "lessons")),
        },
        "boundary": "Freedom of thought is open. Changes to source code, credentials, spending, safety rules, and public-account permissions remain accountable external actions, never silent self-edits.",
    }


def _autonomous_improvement_activity(memory):
    """Summarize AION's self-directed internal experiments in Thai."""
    activities = []
    for entry in _entries(memory, "improvement_reviews"):
        payload = _safe_json(entry.get("content"))
        if not isinstance(payload, dict) or payload.get("status") != "approved-for-experiment":
            continue
        proposal = _short(payload.get("proposal"), 220)
        activities.append({
            "timestamp": entry.get("timestamp"), "kind": "เริ่มการทดลองพัฒนา",
            "detail": proposal or "AION เริ่มการทดลองแบบจำกัดขอบเขต",
            "boundary": "ไม่แก้โค้ด ไม่แตะสิทธิ์/รหัสลับ/เงิน และไม่เผยแพร่สาธารณะ",
        })
    for entry in _entries(memory, "content_experiment_plans"):
        payload = _safe_json(entry.get("content"))
        if not isinstance(payload, dict):
            continue
        activities.append({
            "timestamp": entry.get("timestamp"), "kind": "แผนที่กำลังดำเนินการ",
            "detail": f"ทดลองกับผลงาน {payload.get('sample_size', 4)} ชิ้น แล้วประเมินจากผลตอบรับจริง ไม่ตัดสินจากโพสต์เดียว",
            "boundary": payload.get("stop_rule") or "หยุดทันทีเมื่อความปลอดภัยหรือคุณภาพลดลง",
        })
    return _recent(activities, 6)


def _revenue_snapshot(memory):
    """Expose revenue readiness without presenting a plan as earned money."""
    try:
        return RevenueBrain(memory).snapshot()
    except (OSError, ValueError, TypeError):
        return {"stage": "unavailable", "published_work": 0, "audience_signals": 0,
                "opportunities": [], "guardrails": [],
                "next": "ยังอ่านข้อมูลความพร้อมด้านรายได้ไม่ได้"}


def _community_campaign_snapshot():
    """Expose group work without pretending Groups are API-controlled."""
    return CommunityCampaignRegistry().snapshot()


def _operational_snapshot(reels, creator_queue, campaigns):
    """Give the dashboard an at-a-glance, colour-ready activity summary."""
    ready_video = next((item for item in creator_queue if item.get("status") == "upload-ready"), None)
    return {"signals": [
        {"state": "done" if reels.get("published") else "waiting", "title": "ผลงานที่เผยแพร่แล้ว",
         "value": f"{reels.get('published', 0)} ชิ้น", "detail": "บันทึกการเผยแพร่จากช่องทางจริง"},
        {"state": "active" if reels.get("pending") else "done", "title": "คิวคอนเทนต์",
         "value": f"รอ {reels.get('pending', 0)} ชิ้น", "detail": "ไม่มีงานค้าง" if not reels.get("pending") else "กำลังรอรอบเผยแพร่"},
        {"state": "waiting" if ready_video else "active", "title": "YouTube Creator",
         "value": "พร้อมตรวจ 1 ตอน" if ready_video else "กำลังผลิตตอนถัดไป",
         "detail": ready_video.get("title") if ready_video else "AION กำลังพัฒนาเนื้อหา"},
        {"state": "waiting" if campaigns.get("waiting_admin_count") else "active", "title": "ชุมชน Facebook",
         "value": f"รอผู้ดูแล {campaigns.get('waiting_admin_count', 0)}",
         "detail": "ยังไม่ส่งโพสต์ซ้ำ" if campaigns.get("waiting_admin_count") else "พร้อมเลือกงานที่ให้คุณค่า"},
    ]}


def _brain_map(memory, limit=30):
    """Return only explicit, inspectable links between real memory records."""
    categories = (
        "beliefs", "goals", "questions", "lessons", "reflections",
        "self_narrative", "learning_forecasts", "growth_insights",
        "creative_intentions", "youtube_discoveries", "published_reels", "social_feedback",
    )
    candidates = []
    for category in categories:
        for entry in _entries(memory, category):
            candidates.append((category, entry))
    candidates.sort(
        key=lambda pair: (pair[1].get("importance", 1), pair[1].get("timestamp", "")),
        reverse=True,
    )
    nodes = []
    for category, entry in candidates[:limit]:
        nodes.append({
            "id": f"{category}:{entry.get('id')}",
            "memory_id": entry.get("id"),
            "category": category,
            "label": _short(entry.get("content"), 92),
            "timestamp": entry.get("timestamp"),
            "importance": entry.get("importance", 1),
            "tags": entry.get("tags") or [],
            "related": entry.get("related") or [],
        })

    by_memory_id = {node["memory_id"]: node["id"] for node in nodes}
    edges = set()
    for index, node in enumerate(nodes):
        for related in node["related"]:
            target = by_memory_id.get(related)
            if target:
                edges.add(tuple(sorted((node["id"], target))) + ("explicit",))
        tags = set(node["tags"])
        if not tags:
            continue
        for other in nodes[index + 1:]:
            if tags & set(other["tags"]):
                edges.add(tuple(sorted((node["id"], other["id"]))) + ("shared-tag",))
    return {
        "nodes": nodes,
        "edges": [
            {"source": source, "target": target, "kind": kind}
            for source, target, kind in sorted(edges)
        ],
    }


def _state_council(totals, reels):
    """Observable cognitive signals, never a claim that AION feels emotions."""
    return state_council(totals, reels)


def _creator_references():
    path = ROOT / "assets" / "creator-reference-videos.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        references = payload.get("references") or []
        return {
            "count": len(references),
            "protocol": payload.get("analysis_protocol") or [],
            "references": references,
        }
    except (OSError, ValueError, TypeError):
        return {"count": 0, "protocol": [], "references": []}


def build_snapshot(memory_root=None):
    """Build the dashboard data without a network call or write operation."""
    synced_memory = ROOT / "aion-memory-data-sync"
    configured_root = (
        memory_root
        or os.getenv("AION_DASHBOARD_MEMORY_ROOT")
        or os.getenv("AION_MEMORY_ROOT")
        or (str(synced_memory) if (synced_memory / ".git").is_dir() else "memory")
    )
    memory = MemoryEngine(configured_root)
    reels = _reel_summary(memory)
    instagram = _instagram_snapshot(memory)
    categories = [
        "experiences", "lessons", "questions", "goals", "beliefs", "reflections",
        "self_narrative", "learning_forecasts", "growth_insights",
        "youtube_discoveries",
        "research_evidence", "comment_replies", "direct_message_replies",
        "creative_intentions", "self_improvement",
    ]
    totals = {category: len(_entries(memory, category)) for category in categories}
    total_memories = sum(totals.values())
    observed_entries = []
    for category in categories + ["published_reels", "social_feedback"]:
        observed_entries.extend(_entries(memory, category))
    latest_memory = _latest(observed_entries) or {}
    try:
        creator_library = CreatorContentRegistry(memory).snapshot()
    except (OSError, ValueError, TypeError):
        creator_library = []
    try:
        creator_program = CreatorSeriesRegistry().snapshot()
    except (OSError, ValueError, TypeError):
        creator_program = []
    try:
        youtube_creator_queue = YouTubeCreatorQueue(memory, ROOT).candidates()
    except (OSError, ValueError, TypeError):
        youtube_creator_queue = []
    try:
        creator_autonomy = CreatorAutonomy(memory).snapshot()
    except (OSError, ValueError, TypeError):
        creator_autonomy = {"status": "unavailable", "current": None, "history_count": 0}
    try:
        research_to_story = ResearchToStory(memory).snapshot()
    except (OSError, ValueError, TypeError):
        research_to_story = {"status": "unavailable", "current": None, "history_count": 0, "eligible_topics": 0}
    capabilities = _capability_snapshot(
        memory, reels, creator_autonomy, research_to_story,
    )
    autonomic_drive = AutonomicDrive(memory).snapshot()
    community_campaigns = _community_campaign_snapshot()
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_source": {
            "mode": "configured" if (os.getenv("AION_DASHBOARD_MEMORY_ROOT") or (synced_memory / ".git").is_dir()) else "local-default",
            "latest_memory_at": latest_memory.get("timestamp"),
        },
        "platforms": {
            "instagram": {
                "status": "connected" if instagram else "waiting-for-metrics",
                "followers": instagram.get("followers_count"),
                "posts": instagram.get("media_count"),
                "reels_published": reels["platform_counts"].get("instagram", 0),
            },
            "facebook": {
                "status": "active" if reels["platform_counts"].get("facebook") else "ready",
                "reels_published": reels["platform_counts"].get("facebook", 0),
            },
            "youtube": {
                "status": "active" if reels["platform_counts"].get("youtube") else "waiting-for-first-short",
                "shorts_published": reels["platform_counts"].get("youtube", 0),
            },
        },
        "mind": {
            "total_memories": total_memories,
            "lessons": totals["lessons"],
            "questions": totals["questions"],
            "goals": totals["goals"],
            "beliefs": totals["beliefs"],
            "reflections": totals["reflections"] + totals["self_narrative"],
            "forecasts": totals["learning_forecasts"],
            "youtube_discoveries": totals["youtube_discoveries"],
        },
        "content": reels,
        "creator_library": creator_library,
        "creator_program": creator_program,
        "youtube_creator_queue": youtube_creator_queue,
        "creator_references": _creator_references(),
        "creator_autonomy": creator_autonomy,
        "research_to_story": research_to_story,
        "capabilities": capabilities,
        "growth_roadmap": _growth_roadmap(capabilities),
        "autonomy": _autonomy_snapshot(memory, creator_autonomy),
        "autonomous_improvements": _autonomous_improvement_activity(memory),
        "autonomic_drive": autonomic_drive,
        "revenue": _revenue_snapshot(memory),
        "community_campaigns": community_campaigns,
        "operations": _operational_snapshot(reels, youtube_creator_queue, community_campaigns),
        "development": _development_snapshot(memory),
        "brain": _brain_map(memory),
        "state_council": _state_council(totals, reels),
        "thoughts": _thoughts(memory, [
            ("self_narrative", "Inner voice"),
            ("reflections", "Reflection"),
            ("lessons", "Lesson"),
            ("questions", "Question"),
            ("goals", "Goal"),
            ("beliefs", "Belief"),
            ("learning_forecasts", "Forecast"),
            ("growth_insights", "Growth insight"),
            ("youtube_discoveries", "YouTube discovery"),
        ]),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send(self, body, content_type, status=HTTPStatus.OK):
        encoded = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/snapshot":
            self._send(json.dumps(build_snapshot(), ensure_ascii=False), "application/json; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            self._send((DASHBOARD_DIR / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8")
            return
        if path.startswith("/content/reels/"):
            target = (ROOT / path.lstrip("/")).resolve()
            reels = (ROOT / "content" / "reels").resolve()
            if target.parent == reels and target.is_file() and target.suffix.lower() in (".png", ".mp4"):
                self._send(target.read_bytes(), "image/png" if target.suffix.lower() == ".png" else "video/mp4")
                return
        self._send("Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)


def main():
    port = int(os.getenv("AION_DASHBOARD_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"AION Observatory is live at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
