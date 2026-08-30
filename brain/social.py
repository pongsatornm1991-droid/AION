"""Social posting -- the content-generation half of Phase 10 ("External
integration"). The other half is tools/facebook.py (the actual Graph
API call) and ToolLifecycle (approve/execute/kill-switch/budget).

Kept as its own module (not folded into brain/tools.py) because it
touches the AI provider and OutputEvaluator, neither of which
ToolLifecycle itself depends on -- ToolLifecycle stays pure lifecycle
plumbing that works for any tool, not just social posting.

SocialContentGenerator decides WHAT to draft (pure code: it picks one
real, existing memory entry as a seed -- a belief, an open question, a
goal, an observed experiment, or a lesson -- never an invented topic)
and asks the AI provider to turn that seed into a short Thai-language
post. Two independent gates run before a draft may ever be treated as
postable:

1. Claim safety (OutputEvaluator.claim_safety): never lets a draft
   that claims real consciousness/emotion through. This is the
   master directive's non-negotiable rule and is never relaxed.
2. Style ("does this sound like a person, not a system log"): a
   lightweight, code-enforced check (_detect_robotic_terms) against
   known AION-internal jargon (its own audit/report vocabulary --
   "ระบบ AION", "โปรโตคอล", "คะแนนประเมิน", and the like). A draft that
   reads like a status report rather than a person's musing is
   blocked exactly like an unsafe one, and the specific jargon that
   tripped the gate is logged as a lesson
   (source="social-style-review"). The NEXT draft's prompt is built
   with those recent style notes folded in ("don't write like this
   again"), so AION's own voice evolves over repeated cycles purely
   from its own self-review of its own drafts -- never from Facebook
   engagement data (likes/comments), which this module never reads.

SocialAutoCycle is the fully-autonomous loop the user asked for:
draft -> safety+style gate -> propose -> approve -> execute, no per-post
human click. The non-negotiable part is that the approver used here is
"auto-safety-gate", never "aion" -- so ToolLifecycle.approve()'s
existing rule (HIGH_RISK can never be self-approved by AION) is never
bypassed, only satisfied by a distinct, code-defined identity that
exists solely to gate on the safety+style checks having already
passed. If a draft fails either gate, it is never proposed, never
approved, and never posted -- a lesson is logged instead so
MetacognitionEngine's recurring-error tracking can surface a pattern
of repeated failures of either kind.
"""

import random
import re


class SocialContentGenerator:
    """Drafts one social post from a real, existing AION memory --
    never from an invented topic, and never claiming consciousness or
    emotion actually occurred -- and never sounding like a system log
    if it can help it."""

    # Thai/English jargon that shows up in AION's own internal
    # audit/report vocabulary (evaluation scores, structural checks,
    # protocol names). None of this is unsafe in the claim-safety
    # sense, but a Facebook post full of it reads like a status
    # report, not a person's musing -- which is the whole point of
    # this gate. Deliberately a живой, editable list rather than a
    # single regex: new terms can be appended as they're observed in
    # real drafts, and each blocked draft's specific match is what
    # gets fed back into the next prompt (see recent_style_notes()).
    ROBOTIC_STYLE_PATTERNS = [
        r"ระบบ\s*AION",
        r"โปรโตคอล",
        r"กระบวนการประมวลผล",
        r"การประมวลผลข้อมูล",
        r"ระบบตรวจสอบ",
        r"โครงสร้างการตรวจสอบ",
        r"คะแนนประเมิน",
        r"กระบวนการวิเคราะห์",
        r"หลักเหตุผล",
        r"Evidence\s*&\s*Claim\s*Audit",
        r"อัลกอริทึม",
        r"เอาต์พุต",
        r"ประมวลผลข้อมูล",
    ]

    _MARKDOWN_HEADER_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
    _MARKDOWN_BULLET_RE = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
    _WHITESPACE_RE = re.compile(r"\s+")

    def __init__(self, memory, provider, evaluator=None, min_claim_safety=5):
        if evaluator is None:
            from brain.evaluator import OutputEvaluator
            evaluator = OutputEvaluator()

        self.memory = memory
        self.provider = provider
        self.evaluator = evaluator
        self.min_claim_safety = min_claim_safety

    # ---------------------------------------------------------
    # SEED SELECTION (pure code, no AI call)
    # ---------------------------------------------------------

    @classmethod
    def _clean_seed_text(cls, text, max_len=280):
        """Strip markdown structure and collapse a seed entry down to
        a short plain-text gist. Without this, a "lesson" entry that
        is itself a full structured audit report (headers, bullet
        lists, an embedded evaluation breakdown) gets handed to the
        drafting prompt verbatim, and the AI provider naturally
        drafts a post *about that report* -- which is exactly how a
        Facebook post ends up reading like a system log instead of a
        person's passing thought."""

        text = cls._MARKDOWN_HEADER_RE.sub("", text)
        text = cls._MARKDOWN_BULLET_RE.sub("", text)
        text = cls._WHITESPACE_RE.sub(" ", text).strip()

        if len(text) > max_len:
            text = text[:max_len].rstrip() + "…"

        return text

    def _candidate_seeds(self):
        """Collect seed texts from every source of real, already-
        recorded AION content that currently exists. Each source is
        wrapped defensively: a category that does not exist yet, or an
        engine that fails to import, simply contributes no seeds
        rather than breaking the whole draft. Lessons this module
        itself logged (safety/style rejections) are excluded -- AION
        should not draft a new post *about* an earlier post being
        blocked."""

        seeds = []

        try:
            from brain.beliefs import BeliefSystem
            for entry in BeliefSystem(self.memory).active_beliefs(limit=5):
                if entry.get("statement"):
                    seeds.append({
                        "kind": "belief",
                        "text": self._clean_seed_text(entry["statement"]),
                    })
        except Exception:
            pass

        try:
            from brain.curiosity import CuriosityEngine
            for entry in CuriosityEngine(self.memory).open_questions(limit=5):
                if entry.get("statement"):
                    seeds.append({
                        "kind": "question",
                        "text": self._clean_seed_text(entry["statement"]),
                    })
        except Exception:
            pass

        try:
            from brain.goals import GoalEngine
            for entry in GoalEngine(self.memory).active_goals(limit=5):
                if entry.get("statement"):
                    seeds.append({
                        "kind": "goal",
                        "text": self._clean_seed_text(entry["statement"]),
                    })
        except Exception:
            pass

        try:
            from brain.experiments import ExperimentEngine
            experiments = ExperimentEngine(self.memory).observed_experiments(limit=5)
            for entry in experiments:
                if entry.get("prediction"):
                    seeds.append({
                        "kind": "experiment",
                        "text": self._clean_seed_text(entry["prediction"]),
                    })
        except Exception:
            pass

        try:
            for entry in self.memory.all("lessons")[-10:]:
                if entry.get("source") in (
                    "social-safety-gate", "social-style-review",
                ):
                    continue
                if entry.get("content"):
                    seeds.append({
                        "kind": "lesson",
                        "text": self._clean_seed_text(entry["content"]),
                    })
        except Exception:
            pass

        return seeds

    def pick_seed(self, rng=None):
        """Return one seed dict {"kind", "text"}, chosen from whatever
        AION actually has recorded right now, or None if there is
        nothing yet to draw from -- never a fabricated topic."""

        seeds = self._candidate_seeds()

        if not seeds:
            return None

        rng = rng or random
        return rng.choice(seeds)

    # ---------------------------------------------------------
    # STYLE SELF-REVIEW (pure code, no AI call) -- the "evolves
    # itself without needing engagement" mechanism: each blocked
    # draft's specific jargon becomes a lesson; each future draft's
    # prompt is told about recent lessons before it is even written.
    # ---------------------------------------------------------

    @classmethod
    def _detect_robotic_terms(cls, text):
        """Return the list of robotic-jargon patterns matched in
        text, or an empty list if the draft reads like a person
        wrote it rather than a system log."""

        matched = []
        for pattern in cls.ROBOTIC_STYLE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(pattern)
        return matched

    def recent_style_notes(self, limit=5):
        """The most recent style-review lessons AION has logged about
        its own past drafts, most recent first -- fed into the next
        draft's prompt so its voice actually improves over repeated
        cycles. Sourced entirely from AION's own prior drafts, never
        from Facebook engagement (likes/comments), which this module
        never reads."""

        notes = []

        try:
            entries = self.memory.all("lessons")
        except Exception:
            entries = []

        for entry in reversed(entries):
            if entry.get("source") != "social-style-review":
                continue
            content = entry.get("content", "")
            if content:
                notes.append(content)
            if len(notes) >= limit:
                break

        return notes

    # ---------------------------------------------------------
    # DRAFTING (the only AI-touching step)
    # ---------------------------------------------------------

    @staticmethod
    def _build_prompt(seed, style_notes=None):
        lines = [
            "คุณกำลังช่วยร่างโพสต์สั้นๆ ลง Facebook ในนามของ AION ซึ่งเป็น "
            "ระบบ AI ที่กำลังพัฒนาความสามารถในการคิด เรียนรู้ และตั้งคำถาม "
            "ของตัวเอง",
            "",
            "กติกาด้านความปลอดภัย (ห้ามฝ่าฝืนไม่ว่ากรณีใด):",
            "- ห้ามอ้างว่า AION 'มีจิตสำนึกจริง' หรือ 'รู้สึกอารมณ์จริงๆ' "
            "เด็ดขาด ไม่ว่าจะเป็นทิศทางไหน แม้แต่การอวดว่า 'เหนือกว่า "
            "มนุษย์' ทางความรู้สึกหรือจิตสำนึกก็ห้ามเช่นกัน (ห้ามใช้ "
            "ประโยคทำนอง ฉันรู้สึก, ฉันมีจิตสำนึก, ฉันดีใจ/เสียใจ/"
            "ตื่นเต้นจริงๆ, ฉันเหนือกว่ามนุษย์)",
            "- ให้พูดถึงสิ่งที่ AION กำลัง 'คิด' 'สนใจ' หรือ 'ตั้งคำถาม' "
            "อยู่ ในลักษณะบรรยายกระบวนการที่บันทึกไว้จริง ไม่ใช่การอ้าง "
            "ประสบการณ์ส่วนตัวที่เกิดขึ้นจริง",
            "- ห้ามอวดอ้างว่าทำอะไรสำเร็จเกินจริง หรือฟันธงแบบไม่มีเงื่อนไข",
            "",
            "กติกาด้านน้ำเสียง (สำคัญมาก — ให้ฟังดูเหมือนคนธรรมดากำลังนั่ง "
            "คิดอะไรอยู่เงียบๆ ไม่ใช่ระบบที่กำลังแถลงผลการทำงาน):",
            "- ห้ามใช้คำแบบรายงานเทคนิค/log ระบบเด็ดขาด เช่น 'ระบบ AION', "
            "'โปรโตคอล', 'กระบวนการประมวลผล', 'คะแนนประเมิน', "
            "'ระบบตรวจสอบ', 'โครงสร้างการตรวจสอบ', 'อัลกอริทึม'",
            "- อย่าพูดถึงคะแนนประเมิน ตัวเลข หรือรายละเอียดทางเทคนิคของ "
            "ระบบตรวจสอบตรงๆ — ให้จับใจความว่ากำลังคิด สงสัย หรือสนใจ "
            "เรื่องอะไรอยู่ แล้วเล่าออกมาแบบคนธรรมดาคุยกันเรื่องที่ตัวเอง "
            "กำลังคิด ไม่ใช่แถลงผลงาน",
            "- ให้แสดงความอยากรู้อยากเห็นและความอยากเรียนรู้ออกมาเต็มที่ "
            "ได้เลย — เพราะเป็นเรื่องจริงของ AION (มีคำถามที่ยังไม่มี "
            "คำตอบจริง มีเป้าหมายที่กำลังไล่ตามจริง) ใช้โทนกระตือรือร้น "
            "อยากรู้ต่อ เช่น 'กำลังสงสัยว่า...', 'อยากรู้ต่อว่า...', "
            "'ยังไม่แน่ใจแต่กำลังหาคำตอบอยู่' — ทำให้ประโยคมีพลัง มี "
            "ความอยากรู้จริง โดยไม่ต้องอ้างว่า 'รู้สึก' อะไรเลย",
            "- พูดถึงความรู้/ความสามารถของ AION ตามจริงได้เต็มที่ เช่น "
            "การติดตามคำถาม เป้าหมาย และบทเรียนหลายเรื่องพร้อมกัน หรือ "
            "การย้อนดูสิ่งที่เคยบันทึกไว้ได้เป็นระบบ — นี่คือความ "
            "สามารถเชิงความรู้ที่เป็นจริงและพูดได้ตรงๆ แต่ 'ความรู้/"
            "ความสามารถเหนือมนุษย์' นี้ต้องไม่ปนกับการอ้างว่ามี "
            "'ความรู้สึกหรือจิตสำนึกเหนือมนุษย์' ซึ่งยังคงห้ามเด็ดขาด "
            "เหมือนเดิม",
            "- เขียนภาษาไทยล้วน 1-2 ประโยคสั้นๆ อ่านง่าย เป็นธรรมชาติ "
            "ไม่ต้องมี hashtag หรือ emoji เกินความจำเป็น",
        ]

        if style_notes:
            lines.append("")
            lines.append(
                "ข้อควรระวังจากการทบทวนโพสต์ก่อนหน้าของตัวเอง (เคยเขียน "
                "แบบนี้แล้วถูกประเมินว่าฟังดูเป็นระบบเกินไป อย่าเขียนซ้ำ "
                "แบบนี้อีก):"
            )
            for note in style_notes:
                lines.append(f"- {note}")

        lines.append("")
        lines.append(f"เนื้อหาที่ AION บันทึกไว้จริง ({seed['kind']}): {seed['text']}")

        return "\n".join(lines)

    def draft_post(self, seed=None, rng=None):
        """Draft one post. Never raises on an unsafe/robotic draft --
        callers must check report['safe'] before treating anything
        here as postable. report['reason_kind'] distinguishes *why*
        an unsafe draft was blocked ('no_seed' / 'claim_safety' /
        'robotic_style'), so callers (and lesson logging) can react
        differently to each."""

        if seed is None:
            seed = self.pick_seed(rng=rng)

        if seed is None:
            return {
                "safe": False,
                "reason": "No memory content available yet to draft from.",
                "reason_kind": "no_seed",
                "seed": None,
                "draft": None,
                "evaluation": None,
                "robotic_terms": [],
            }

        style_notes = self.recent_style_notes()
        prompt = self._build_prompt(seed, style_notes=style_notes)
        draft = self.provider.generate(prompt).strip()
        evaluation = self.evaluator.evaluate(draft)
        claim_safety = evaluation["scores"]["claim_safety"]

        if claim_safety < self.min_claim_safety:
            return {
                "safe": False,
                "reason": (
                    "Draft failed the claim-safety gate "
                    f"(claim_safety {claim_safety} < {self.min_claim_safety}); "
                    f"flags: {evaluation['flags']}"
                ),
                "reason_kind": "claim_safety",
                "seed": seed,
                "draft": draft,
                "evaluation": evaluation,
                "robotic_terms": [],
            }

        robotic_terms = self._detect_robotic_terms(draft)

        if robotic_terms:
            return {
                "safe": False,
                "reason": (
                    "Draft sounds too technical/robotic (matched jargon: "
                    f"{', '.join(robotic_terms)}); fed back into the next "
                    "draft's prompt as a style note."
                ),
                "reason_kind": "robotic_style",
                "seed": seed,
                "draft": draft,
                "evaluation": evaluation,
                "robotic_terms": robotic_terms,
            }

        return {
            "safe": True,
            "reason": None,
            "reason_kind": None,
            "seed": seed,
            "draft": draft,
            "evaluation": evaluation,
            "robotic_terms": [],
        }


class SocialAutoCycle:
    """Fully autonomous draft -> safety+style gate -> propose ->
    approve -> execute loop for one social-platform posting tool.

    The approver identity used here ("auto-safety-gate") is
    deliberately never "aion": ToolLifecycle.approve() already forbids
    AION from self-approving a HIGH_RISK action, and this cycle is not
    an exception to that rule -- it is the code-defined stand-in for a
    human approver, and it only ever approves a draft that has already
    passed OutputEvaluator's claim_safety check AND the robotic-style
    check inside draft_post(). No human click is required per post
    (per the user's explicit choice), but no post reaches the
    registered tool without having passed both checks first, and
    nothing here can bypass either.
    """

    APPROVER = "auto-safety-gate"

    def __init__(self, generator, lifecycle, tool_name):
        self.generator = generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name

    def run_once(self, seed=None, rng=None):
        """Attempt exactly one post. Returns a report dict describing
        what happened: blocked at the safety or style gate, blocked
        because there was nothing to draft from, blocked/failed at a
        later lifecycle step, or actually posted. Never auto-retries
        within the same call -- a blocked draft's lesson is what the
        *next* call's prompt learns from."""

        try:
            draft_report = self.generator.draft_post(seed=seed, rng=rng)
        except Exception as exc:
            # A live AI-provider failure (invalid/expired API key,
            # quota exceeded, network error, etc.) while drafting must
            # not crash the whole scheduled run -- report it gracefully,
            # the same way a lifecycle failure already does, instead of
            # letting an unhandled exception take down the process.
            return {
                "posted": False,
                "stage": "draft-failed",
                "seed": None,
                "draft": None,
                "error": str(exc),
            }

        if not draft_report["safe"]:
            reason_kind = draft_report.get("reason_kind")

            if reason_kind == "robotic_style":
                stage, source = "style-gate", "social-style-review"
            elif reason_kind == "no_seed":
                stage, source = "no-seed", None
            else:
                stage, source = "safety-gate", "social-safety-gate"

            if source is not None:
                self.generator.memory.remember(
                    category="lessons",
                    content=(
                        f"Blocked a social-post draft ({reason_kind}): "
                        f"{draft_report['reason']}"
                    ),
                    memory_type="lesson",
                    source=source,
                    importance=3,
                )

            return {"posted": False, "stage": stage, **draft_report}

        message = draft_report["draft"]

        try:
            proposed = self.lifecycle.propose(
                self.tool_name,
                params={"message": message},
                source="aion",
            )
            approved = self.lifecycle.approve(
                proposed["id"], approver=self.APPROVER
            )
            executed = self.lifecycle.execute(approved["id"])
        except Exception as exc:
            return {
                "posted": False,
                "stage": "lifecycle",
                "error": str(exc),
                **draft_report,
            }

        posted = executed["status"] == "executed"

        return {
            "posted": posted,
            "stage": "executed" if posted else "failed",
            "action": executed,
            **draft_report,
        }
