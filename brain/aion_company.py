"""AION's internal company structure: specialist roles with clear handoffs.

The company is deliberately an orchestration model, not a claim that several
independent people exist.  Each department names a real capability, produces
an inspectable deliverable, and reports to AION as creative director.
Credentials, spending, and safety-rule changes remain outside the company's
autonomous authority. Public publishing is delegated to AION after its quality
gate, under the project policy.
"""

from pathlib import Path

from brain.autonomy_policy import AutonomyPolicy
from brain.company_operations import CompanyOperations


class AionCompany:
    """Return a live, inspectable operating board for AION Studio."""

    def __init__(self, memory, root=None):
        self.memory = memory
        self.root = Path(root or Path(__file__).resolve().parents[1])

    def _count(self, category):
        try:
            return len(self.memory.all(category))
        except (OSError, ValueError, TypeError):
            return 0

    def board(self, episodes, queue):
        images = len(list((self.root / "content" / "images").glob("*.png")))
        rendered = sum(1 for item in queue if item.get("video_exists"))
        ready = sum(1 for item in queue if item.get("status") == "upload-ready")
        policy = AutonomyPolicy(self.root)
        operations = CompanyOperations(self.root).audit()
        published = self._count("published_reels")
        return {
            "leadership": {
                "chair": "ประธาน — กำหนดวิสัยทัศน์ และอนุมัติเฉพาะเงิน สัญญา สิทธิ์บัญชี และข้อมูลรับรอง",
                "ceo": "AION — เลือกโจทย์ ประสานทีม ตรวจคุณภาพ และเผยแพร่ผลงานสาธารณะที่ผ่านเกณฑ์",
            },
            "authority": {
                "public_publishing": policy.public_publishing_summary(),
                "mode": policy.publishing_mode,
                "protected": policy.data.get("chair_approval_required", []),
            },
            "operations": operations,
            "boundary": "AION และทีมเผยแพร่ผลงานสาธารณะที่ผ่าน Quality Gate ได้เอง แต่ห้ามเปลี่ยนสิทธิ์หรือข้อมูลรับรอง ใช้/รับเงิน ทำสัญญา หรือแก้กฎความปลอดภัยเอง",
            "departments": [
                {"id": "research", "name": "ฝ่ายวิจัย", "lead": "Research Agent", "room": "ห้องค้นคว้า",
                 "does": "ค้นหาแหล่งทางการ แยกข้อเท็จจริงจากสิ่งที่ยังไม่แน่ชัด และส่ง research brief", "evidence": f"{sum(item.get('source_count', 0) for item in episodes)} แหล่งอ้างอิงในซีรีส์", "handoff": "ส่ง brief ให้ฝ่ายเรื่องเล่า", "state": "active"},
                {"id": "story", "name": "ฝ่ายเรื่องเล่า", "lead": "Story Agent", "room": "ห้องเรื่องเล่า",
                 "does": "ออกแบบ hook, คุณค่าต่อผู้ชม, บท และ storyboard ที่ AION อยู่ในทุกฉาก", "evidence": f"{len(episodes)} ตอนที่ออกแบบแล้ว", "handoff": "ส่ง storyboard ให้ฝ่ายภาพและเสียง", "state": "active"},
                {"id": "visual", "name": "ฝ่ายภาพ", "lead": "Visual Agent", "room": "ห้องภาพและฉาก",
                 "does": "ผลิตภาพใหม่ตามฉาก รักษาตัวตน AION และจัดการสินทรัพย์ภาพ", "evidence": f"{images} ภาพต้นฉบับ", "handoff": "ส่งฉากที่ตรวจความต่อเนื่องแล้วให้ฝ่ายประกอบ", "state": "active"},
                {"id": "audio", "name": "ฝ่ายเสียงและประกอบ", "lead": "Audio Agent", "room": "ห้องเสียง",
                 "does": "จัดบรรยาย จังหวะ และไฟล์ประกอบหลังภาพและเรื่องผ่านการตรวจ", "evidence": f"{rendered} วิดีโอมีไฟล์พร้อมตรวจ", "handoff": "ส่งวิดีโอร่างให้ฝ่ายคุณภาพ", "state": "ready"},
                {"id": "quality", "name": "ฝ่ายคุณภาพ", "lead": "Quality Agent", "room": "ห้องตรวจและส่งออก",
                 "does": "ตรวจหลักฐาน ขอบเขตความไม่แน่นอน คุณค่าต่อผู้ชม และความครบของงาน", "evidence": f"{ready} ตอนพร้อมให้ AION เผยแพร่", "handoff": "ส่งเฉพาะงานที่ผ่านไปฝ่ายเผยแพร่", "state": "waiting" if ready else "active"},
                {"id": "publishing", "name": "ฝ่ายเผยแพร่และช่องทาง", "lead": "Publishing Agent", "room": "ศูนย์เผยแพร่",
                 "does": "เผยแพร่งานที่ผ่าน Quality Gate ไปยังช่องทางที่เชื่อมต่อ บันทึกผล และหยุดเมื่อข้อกำหนดแพลตฟอร์มไม่ผ่าน", "evidence": f"บันทึกผลงานเผยแพร่ {published} รายการ", "handoff": "ส่งผลจริงให้ฝ่ายผู้ชมและการเติบโต", "state": "active" if policy.public_publishing_enabled else "waiting"},
                {"id": "growth", "name": "ฝ่ายผู้ชมและการเติบโต", "lead": "Growth Agent", "room": "ศูนย์สังเกตการณ์",
                 "does": "อ่านผลตอบรับจริง ค้นหาคำถามที่คนสนใจ และเสนอการทดลองคอนเทนต์อย่างมีขอบเขต", "evidence": f"บันทึกเสียงตอบรับ {self._count('social_feedback')} รายการ", "handoff": "ส่ง insight ให้ AION เลือกทิศทางถัดไป", "state": "active"},
                {"id": "memory", "name": "ฝ่ายความทรงจำและคลังงาน", "lead": "Memory Agent", "room": "คลัง AION",
                 "does": "จัดบทเรียน ความทรงจำ เวอร์ชัน และสินทรัพย์ ป้องกันความซ้ำซ้อนและไฟล์ค้าง", "evidence": f"บทเรียน {self._count('lessons')} รายการ", "handoff": "เก็บร่องรอยให้ทุกฝ่ายตรวจย้อนหลังได้", "state": "active"},
            ],
        }
