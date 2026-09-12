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
from brain.company_work_registry import CompanyWorkRegistry
from brain.company_quality_audit import CompanyQualityAudit


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
        ready = sum(1 for item in queue if item.get("publication_status") == "authorized-for-aion-publish" or item.get("status") == "upload-ready")
        policy = AutonomyPolicy(self.root)
        operations = CompanyOperations(self.root).audit()
        workflow_states = {
            item["department"]: item["state"]
            for item in CompanyWorkRegistry(self.root).snapshot().get("departments", [])
        }
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
            "work_registry": CompanyWorkRegistry(self.root).snapshot(),
            "quality_audit": CompanyQualityAudit(self.root).snapshot(),
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
                {"id": "engineering", "name": "ฝ่ายพัฒนาและความน่าเชื่อถือ", "lead": "Engineering Lead", "room": "ห้องวิศวกรรมระบบ",
                 "does": "ตรวจความพร้อมของโค้ด รันทดสอบ ติดตามข้อผิดพลาด และปล่อยการแก้ไขเฉพาะที่ผ่านการตรวจ", "evidence": "ตรวจโค้ดและ workflow แบบอ่านอย่างเดียว", "handoff": "ส่งผลตรวจให้ AION และส่งชุดแก้ไขที่ผ่าน QA เข้าสู่ release", "state": workflow_states.get("engineering", "unknown")},
            ],
            "agents": [
                {"name": "Inquiry Scout", "department": "ฝ่ายวิจัย", "does": "เลือกคำถามที่มีหลักฐานพอให้ค้นต่อ", "handoff": "ส่งคำถามให้ Evidence Analyst", "state": workflow_states.get("research", "unknown")},
                {"name": "Evidence Analyst", "department": "ฝ่ายวิจัย", "does": "ตรวจแหล่งทางการ แยกข้อเท็จจริงและความไม่แน่นอน", "handoff": "ส่ง research brief ให้ Story Architect", "state": workflow_states.get("research", "unknown")},
                {"name": "Story Architect", "department": "ฝ่ายเรื่องเล่า", "does": "เปลี่ยนหลักฐานเป็นเรื่องที่ทุกวัยติดตามได้ โดย AION เป็นผู้ดำเนินเรื่อง", "handoff": "ส่ง storyboard ให้ Visual Director", "state": workflow_states.get("story", "unknown")},
                {"name": "Visual Director", "department": "ฝ่ายภาพ", "does": "สร้างภาพใหม่รายฉากและตรวจไม่ให้ใช้ภาพเดิมซ้ำเป็นทางลัด", "handoff": "ส่งฉากให้ Audio Producer และ Quality Gate", "state": workflow_states.get("visual", "unknown")},
                {"name": "Quality Guardian", "department": "ฝ่ายคุณภาพ", "does": "ตรวจประโยชน์ต่อผู้ชม หลักฐาน ความไม่แน่นอน และข้อกำหนดแพลตฟอร์ม", "handoff": "ปล่อยเฉพาะงานที่ผ่านให้ Publishing Agent", "state": workflow_states.get("quality", "unknown")},
                {"name": "Video QA Agent", "department": "ฝ่ายคุณภาพ", "does": "ตรวจวิดีโอจริง: ไฟล์ เสียง สัดส่วน ความละเอียด ความยาว และเฟรมตัวอย่างก่อนเผยแพร่", "handoff": "ส่งเฉพาะคลิปที่ผ่าน Technical/Frame QC ให้ Quality Guardian", "state": workflow_states.get("quality", "unknown")},
                {"name": "Publishing Agent", "department": "ฝ่ายเผยแพร่", "does": "เผยแพร่งานผ่านเกณฑ์และบันทึกผลจริงจากช่องทาง", "handoff": "ส่งผลให้ Growth Analyst", "state": workflow_states.get("publishing", "unknown")},
                {"name": "Dev Agent", "department": "ฝ่ายพัฒนาและความน่าเชื่อถือ", "does": "วิเคราะห์บั๊กและสร้างชุดแก้ไขที่มีขอบเขต", "handoff": "ส่ง patch ให้ QA Agent ตรวจ", "state": workflow_states.get("engineering", "unknown")},
                {"name": "QA Agent", "department": "ฝ่ายพัฒนาและความน่าเชื่อถือ", "does": "รันทดสอบและกัน regression ก่อน release", "handoff": "ส่งเฉพาะผลที่ผ่านให้ Release Agent", "state": workflow_states.get("engineering", "unknown")},
                {"name": "Reliability Monitor", "department": "ฝ่ายพัฒนาและความน่าเชื่อถือ", "does": "ตรวจ workflow และส่วนประกอบหลักโดยไม่แตะบัญชีหรือ secrets", "handoff": "แจ้ง Dev Agent เมื่อพบหลักฐานความผิดปกติ", "state": workflow_states.get("engineering", "unknown")},
            ],
        }
