"""Self-improvement proposals -- AION reviews its own recurring failure
patterns and drafts a plain-language diagnosis + suggested fix for a
person to read and act on.

Deliberately NOT wired through brain/tools.py's ToolLifecycle/
ActionLevel machinery: that machinery exists to gate actions that DO
something to the outside world (post, reply, change a bio) before they
are allowed to run. This cycle has no "apply" step at all -- it only
ever writes one memory entry and (like every other drafting cycle)
reports to Telegram -- so there is nothing for a lifecycle to approve.
The safety property here is simpler and stronger than an approval
gate: the code that could execute a proposed fix does not exist in
this project. Turning a proposal into an actual change is a
deliberate, human-initiated step outside this cycle and outside
AION's own automation entirely -- in practice, the same way every real
fix in this project's own history has been made: a person brings the
problem to a developer (or a Claude Code session) who reads the actual
code, writes the fix, tests it, and commits it.

Source data is brain/metacognition.py's MetacognitionEngine.
recurring_error_report(), a literal count of `lessons` entries grouped
by their `source` field -- already populated today by the safety/style
gates every drafting cycle runs through (social-safety-gate,
social-style-review, comment-style-review, learning-style-review, and
so on). Nothing here reads a raw stack trace or touches this repo's
own source files; the "error" in "recurring error" is a recurring
*content* failure pattern, which is exactly the kind of thing an AI
provider can meaningfully diagnose and suggest a fix for (a prompt
change, a new safety-gate pattern, or, when the pattern clearly points
at code, a description of what to change and where) -- always framed
as a suggestion for a person to evaluate, never as a diff this cycle
applies itself.
"""


class SelfImprovementCycle:
    """propose_fix(): find the most-recurring, not-yet-proposed lesson
    source and draft one diagnosis + suggested-fix note about it.

    Gated exactly like WebLearningGenerator.draft_answer() and
    SocialContentGenerator.draft_post(): claim safety first (the
    master directive's non-negotiable rule applies here too -- a
    self-improvement note is still AION-authored text that could claim
    real consciousness if the gate were skipped). There is
    deliberately no robotic-style gate on top of it: this text is
    meant for the project's own maintainer, not a public post, so
    sounding technical is fine here.
    """

    CATEGORY = "self_improvement"

    def __init__(self, memory, provider, metacognition=None, evaluator=None, min_claim_safety=5):
        if evaluator is None:
            from brain.evaluator import OutputEvaluator
            evaluator = OutputEvaluator()
        if metacognition is None:
            from brain.metacognition import MetacognitionEngine
            metacognition = MetacognitionEngine(memory)

        self.memory = memory
        self.provider = provider
        self.metacognition = metacognition
        self.evaluator = evaluator
        self.min_claim_safety = min_claim_safety

    def _already_proposed_sources(self):
        """Every error `source` a proposal already exists for, so the
        same recurring pattern is never proposed twice -- a fresh
        proposal only makes sense once the existing one has actually
        been acted on or dismissed by a person, which this cycle has
        no way to know, so it simply does not repeat itself."""

        proposed = set()
        for entry in self.memory.all(self.CATEGORY):
            for tag in entry.get("tags") or []:
                if tag.startswith("error-source:"):
                    proposed.add(tag[len("error-source:"):])
        return proposed

    @staticmethod
    def _build_prompt(source, count, examples):
        lines = [
            "คุณกำลังช่วย AION วิเคราะห์รูปแบบข้อผิดพลาดที่เกิดขึ้นซ้ำๆ ของตัวเอง "
            "เพื่อเสนอแนวทางแก้ไขให้คนดูแลโปรเจกต์พิจารณา",
            "",
            "กติกาสำคัญ:",
            "- นี่คือ 'ข้อเสนอ' สำหรับให้คนอ่านพิจารณาเท่านั้น ไม่ใช่การกระทำจริง "
            "AION จะไม่แก้โค้ดหรือเผยแพร่อะไรเองจากการวิเคราะห์นี้",
            "- ห้ามอ้างว่า AION 'มีจิตสำนึกจริง' หรือ 'รู้สึกอารมณ์จริงๆ'",
            "- เขียนเป็นภาษาไทย กระชับ ชัดเจน ตรงประเด็น",
            "",
            f"รูปแบบที่เกิดซ้ำ: บันทึกที่มาจาก '{source}' เกิดขึ้นแล้ว {count} ครั้ง",
            "",
            "ตัวอย่างบันทึกจริงที่เกิดซ้ำ:",
        ]
        for index, example in enumerate(examples, start=1):
            lines.append(f"{index}. {example}")
        lines.append("")
        lines.append(
            "ตอบกลับมาเป็น 2 ส่วนเท่านั้น ขึ้นบรรทัดใหม่คั่นกัน: "
            "'สาเหตุที่น่าจะเป็น: ...' แล้วตามด้วย 'ข้อเสนอแนะ: ...' "
            "(ข้อเสนอแนะควรระบุให้ชัดว่าควรแก้ตรงไหน เช่น ปรับ prompt, "
            "เพิ่มกติกาในตัวกรองความปลอดภัย/น้ำเสียง, หรือแก้โค้ดไฟล์ใด "
            "ถ้าพอจะบอกได้จากรูปแบบที่เห็น)"
        )
        return "\n".join(lines)

    def propose_fix(self, min_occurrences=3, limit_examples=3):
        """Attempt to draft exactly one self-improvement proposal.

        Returns a report dict with a "stage" key:
        - "no-recurring-pattern": no lesson source has recurred at
          least min_occurrences times yet.
        - "no-new-pattern": every currently-recurring source already
          has a standing proposal (see _already_proposed_sources()).
        - "blocked-safety": the drafted note failed the claim-safety
          gate and was discarded, never saved.
        - "proposed": a new proposal was drafted, safety-gated, and
          recorded in memory (category "self_improvement").
        """

        report = self.metacognition.recurring_error_report(
            min_occurrences=min_occurrences,
        )

        already = self._already_proposed_sources()
        candidates = [
            item for item in report["recurring"]
            if item["source"] not in already
        ]

        if not report["recurring"]:
            return {
                "proposed": False,
                "stage": "no-recurring-pattern",
                "recurring": [],
            }

        if not candidates:
            return {
                "proposed": False,
                "stage": "no-new-pattern",
                "recurring": report["recurring"],
            }

        target = candidates[0]
        source = target["source"]
        count = target["count"]

        lessons = self.memory.all("lessons")
        by_id = {
            lesson["id"]: lesson for lesson in lessons if lesson.get("id")
        }
        examples = []
        for entry_id in target.get("example_ids", [])[:limit_examples]:
            lesson = by_id.get(entry_id)
            if lesson and lesson.get("content"):
                examples.append(lesson["content"])
        if not examples:
            examples = ["(ไม่มีตัวอย่างเนื้อหาเก็บไว้ให้ดูแล้ว)"]

        prompt = self._build_prompt(source, count, examples)
        draft = self.provider.generate(prompt).strip()
        evaluation = self.evaluator.evaluate(draft)
        claim_safety = evaluation["scores"]["claim_safety"]

        if claim_safety < self.min_claim_safety:
            return {
                "proposed": False,
                "stage": "blocked-safety",
                "error_source": source,
                "occurrences": count,
                "draft": draft,
                "evaluation": evaluation,
            }

        saved = self.memory.remember(
            category=self.CATEGORY,
            content=draft,
            memory_type="observation",
            source="self-improvement-cycle",
            importance=3,
            tags=[f"error-source:{source}", f"occurrences:{count}"],
        )

        return {
            "proposed": True,
            "stage": "proposed",
            "error_source": source,
            "occurrences": count,
            "draft": draft,
            "saved": saved,
        }
