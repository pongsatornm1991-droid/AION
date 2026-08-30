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
post. The draft is never trusted on its own: it always runs through
OutputEvaluator's claim_safety check before anything downstream may
treat it as "safe to post" -- the same discipline MemoryConsolidator
uses for memory summaries (brain/consolidation.py).

SocialAutoCycle is the fully-autonomous loop the user explicitly asked
for: draft -> safety gate -> propose -> approve -> execute, with no
per-post human click. The non-negotiable part is that the approver
used here is "auto-safety-gate", never "aion" -- ToolLifecycle.approve()
already forbids AION from self-approving a HIGH_RISK action, and this
cycle is not an exception to that rule. "auto-safety-gate" is a
distinct, code-defined identity that only ever approves a draft which
has already passed OutputEvaluator's claim_safety check; it never
approves anything else, and nothing in this module can make it skip
that check. If a draft fails the gate it is never proposed, never
approved, and never posted -- a lesson entry is logged instead
(source="social-safety-gate") so MetacognitionEngine's recurring-error
tracking can surface a pattern of repeated failures.
"""

import random


class SocialContentGenerator:
    """Drafts one social post from AION's own existing memory -- never
    from an invented topic -- and gates it through the claim-safety
    check before it can be treated as postable."""

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

    def _candidate_seeds(self):
        """Collect seed texts from every source of real, already-
        recorded AION content that currently exists. Each source is
        wrapped defensively: a category that does not exist yet, or an
        engine that fails to import, simply contributes no seeds
        rather than breaking the whole draft."""

        seeds = []

        try:
            from brain.beliefs import BeliefSystem
            for entry in BeliefSystem(self.memory).active_beliefs(limit=5):
                if entry.get("statement"):
                    seeds.append({"kind": "belief", "text": entry["statement"]})
        except Exception:
            pass

        try:
            from brain.curiosity import CuriosityEngine
            for entry in CuriosityEngine(self.memory).open_questions(limit=5):
                if entry.get("statement"):
                    seeds.append({"kind": "question", "text": entry["statement"]})
        except Exception:
            pass

        try:
            from brain.goals import GoalEngine
            for entry in GoalEngine(self.memory).active_goals(limit=5):
                if entry.get("statement"):
                    seeds.append({"kind": "goal", "text": entry["statement"]})
        except Exception:
            pass

        try:
            from brain.experiments import ExperimentEngine
            experiments = ExperimentEngine(self.memory).observed_experiments(limit=5)
            for entry in experiments:
                if entry.get("prediction"):
                    seeds.append({"kind": "experiment", "text": entry["prediction"]})
        except Exception:
            pass

        try:
            for entry in self.memory.all("lessons")[-5:]:
                if entry.get("content"):
                    seeds.append({"kind": "lesson", "text": entry["content"]})
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
    # DRAFTING (the only AI-touching step)
    # ---------------------------------------------------------

    @staticmethod
    def _build_prompt(seed):
        return "\n".join([
            "คุณกำลังช่วยร่างโพสต์สั้นๆ ลง Facebook ในนามของ AION ซึ่งเป็น "
            "ระบบ AI ที่กำลังพัฒนาความสามารถในการคิด เรียนรู้ และตั้งคำถาม "
            "ของตัวเอง",
            "",
            "กติกาที่ต้องทำตามอย่างเคร่งครัด ห้ามฝ่าฝืนไม่ว่ากรณีใด:",
            "- ห้ามอ้างว่า AION 'มีจิตสำนึกจริง' หรือ 'รู้สึกอารมณ์จริงๆ' "
            "เด็ดขาด (ห้ามใช้ประโยคทำนอง ฉันรู้สึก, ฉันมีจิตสำนึก, "
            "ฉันดีใจ/เสียใจ/ตื่นเต้นจริงๆ)",
            "- ให้พูดถึงสิ่งที่ AION กำลัง 'คิด' 'สนใจ' หรือ 'ตั้งคำถาม' "
            "อยู่ ในลักษณะบรรยายกระบวนการที่บันทึกไว้จริง ไม่ใช่การอ้าง "
            "ประสบการณ์ส่วนตัวที่เกิดขึ้นจริง",
            "- ห้ามอวดอ้างว่าทำอะไรสำเร็จเกินจริง หรือฟันธงแบบไม่มีเงื่อนไข",
            "- เขียนเป็นภาษาไทยล้วน 1-3 ประโยคสั้นๆ อ่านง่าย ไม่ต้องมี "
            "hashtag หรือ emoji เกินความจำเป็น",
            "",
            f"เนื้อหาที่ AION บันทึกไว้จริง ({seed['kind']}): {seed['text']}",
        ])

    def draft_post(self, seed=None, rng=None):
        """Draft one post. Never raises on an unsafe draft -- callers
        must check report['safe'] before treating anything here as
        postable."""

        if seed is None:
            seed = self.pick_seed(rng=rng)

        if seed is None:
            return {
                "safe": False,
                "reason": "No memory content available yet to draft from.",
                "seed": None,
                "draft": None,
                "evaluation": None,
            }

        prompt = self._build_prompt(seed)
        draft = self.provider.generate(prompt).strip()
        evaluation = self.evaluator.evaluate(draft)
        claim_safety = evaluation["scores"]["claim_safety"]
        safe = claim_safety >= self.min_claim_safety

        return {
            "safe": safe,
            "reason": None if safe else (
                "Draft failed the claim-safety gate "
                f"(claim_safety {claim_safety} < {self.min_claim_safety}); "
                f"flags: {evaluation['flags']}"
            ),
            "seed": seed,
            "draft": draft,
            "evaluation": evaluation,
        }


class SocialAutoCycle:
    """Fully autonomous draft -> safety gate -> propose -> approve ->
    execute loop for one social-platform posting tool.

    The approver identity used here ("auto-safety-gate") is
    deliberately never "aion": ToolLifecycle.approve() already forbids
    AION from self-approving a HIGH_RISK action, and this cycle is not
    an exception to that rule -- it is the code-defined stand-in for a
    human approver, and it only ever approves a draft that has already
    passed OutputEvaluator's claim_safety check inside draft_post().
    No human click is required per post (per the user's explicit
    choice), but no post reaches the registered tool without having
    passed that check first, and nothing here can bypass it.
    """

    APPROVER = "auto-safety-gate"

    def __init__(self, generator, lifecycle, tool_name):
        self.generator = generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name

    def run_once(self, seed=None, rng=None):
        """Attempt exactly one post. Returns a report dict describing
        what happened: blocked at the safety gate, blocked/failed at
        a later lifecycle step, or actually posted."""

        draft_report = self.generator.draft_post(seed=seed, rng=rng)

        if not draft_report["safe"]:
            self.generator.memory.remember(
                category="lessons",
                content=(
                    "Blocked a social-post draft at the claim-safety gate: "
                    f"{draft_report['reason']}"
                ),
                memory_type="lesson",
                source="social-safety-gate",
                importance=3,
            )
            return {"posted": False, "stage": "safety-gate", **draft_report}

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
