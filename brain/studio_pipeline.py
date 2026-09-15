"""Read the actual Creator Series files as one visible Studio handoff chain."""

from pathlib import Path

from brain.creator_series import CreatorSeriesRegistry


class StudioPipeline:
    STAGES = {
        "storyboard-ready-needs-assets": ("Visual Director", "Audio Producer", "กำลังสร้างภาพรายฉาก"),
        "assets-ready-for-assembly": ("Audio Producer", "Video QA Agent", "ภาพครบ รอประกอบเสียงและวิดีโอ"),
        "production-ready-assets-and-script": ("Video QA Agent", "YouTube Publishing Agent", "วิดีโอและ caption พร้อมตรวจ/ส่งต่อ"),
    }

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def snapshot(self):
        cards = []
        for episode in CreatorSeriesRegistry(self.root).episodes():
            state = self.STAGES.get(episode.get("status"))
            if not state:
                continue
            owner, next_owner, detail = state
            cards.append({
                "task_id": f"studio-{episode['id']}", "lane": "studio-production",
                "title": episode["title"], "status": "in-progress",
                "priority": "urgent", "owner": owner, "next_owner": next_owner,
                "detail": detail, "episode_id": episode["id"],
            })
        return {"active": cards, "total": len(cards)}
