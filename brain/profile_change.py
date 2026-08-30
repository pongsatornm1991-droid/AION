"""Identity-change approval -- Phase 12 ("AION's own presented identity
can change, but only with a real person's explicit approval").

The other halves are tools/facebook.py's get_page_bio()/update_page_bio()
and ToolLifecycle (approve/execute/kill-switch/budget), exactly like
brain/social.py's and brain/comment_reply.py's relationship to their
own tools. This module mirrors both of those deliberately: the same
claim-safety gate, the same robotic-style gate, drafts grounded only in
AION's own real recorded content (never an invented identity).

The one fundamental difference from social.py/comment_reply.py: those
two cycles are fully autonomous end to end (no human click per post/
reply -- the "auto-safety-gate" approver identity satisfies
ToolLifecycle's non-self-approval rule on AION's behalf, once the
content itself has passed both gates). Identity changes are different
on purpose -- see brain/tools.py's ActionLevel.IDENTITY_CHANGE
docstring -- so this module never auto-approves anything. It only ever
gets as far as ToolLifecycle.propose(), then asks a real person to
approve or reject via a Telegram inline button. Only that person's own
button tap ever calls ToolLifecycle.approve()/execute() (or reject()),
using an approver identity derived from their real Telegram user
(never "aion", never "auto-safety-gate") -- so
ToolLifecycle.approve()'s existing rule (IDENTITY_CHANGE can never be
self-approved by AION) is structurally impossible to bypass here: there
is no code path in this module that can call approve() with an
AION-controlled approver string.

Two independent cycles, run separately (see main.py's CLI wiring):

- ProfileChangeCycle.propose_once(): draft -> safety+style gate ->
  propose (never approve/execute) -> send one Telegram message with
  Approve/Reject buttons. Skips drafting a new proposal entirely if
  one is already awaiting approval (ToolLifecycle.actions() is the
  single source of truth for "is one pending" -- no separate
  bookkeeping category is needed for that).
- ProfileChangeCycle.check_approvals_once(): poll Telegram for new
  button taps, and for each one, approve+execute or reject the
  matching proposed action, then acknowledge the tap in Telegram (a
  best-effort UI courtesy -- its failure never undoes an
  already-recorded lifecycle decision). The offset needed to avoid
  re-processing the same Telegram update twice is the one piece of
  state this module keeps of its own (memory category
  "telegram_offsets", most-recent-entry-wins, mirroring how the rest
  of this codebase treats memory as append-only).
"""


class ProfileChangeGenerator:
    """Drafts one revised Facebook Page bio -- gated exactly like
    SocialContentGenerator.draft_post(): claim safety first, then the
    robotic-style tone check. Grounded only in AION's own real,
    already-recorded content (reuses
    SocialContentGenerator._candidate_seeds()), never an invented
    identity."""

    def __init__(self, memory, provider, evaluator=None, min_claim_safety=5):
        if evaluator is None:
            from brain.evaluator import OutputEvaluator
            evaluator = OutputEvaluator()

        self.memory = memory
        self.provider = provider
        self.evaluator = evaluator
        self.min_claim_safety = min_claim_safety

    def _recent_context(self, limit=3):
        """A short gist of what AION has actually recently recorded
        (beliefs/goals/questions/experiments/lessons), reusing
        SocialContentGenerator's own seed collection so a bio draft is
        grounded in real content instead of an invented self-
        description."""

        from brain.social import SocialContentGenerator

        gen = SocialContentGenerator(self.memory, self.provider, evaluator=self.evaluator)
        seeds = gen._candidate_seeds()
        return [seed["text"] for seed in seeds[:limit]]

    @staticmethod
    def _build_prompt(current_bio, context_notes, style_notes=None):
        lines = [
            "คุณกำลังช่วยร่างข้อความ 'เกี่ยวกับ' (about/bio) สั้นๆ ของ "
            "Facebook Page ในนามของ AION ซึ่งเป็นระบบ AI ที่กำลังพัฒนา "
            "ความสามารถในการคิด เรียนรู้ และตั้งคำถามของตัวเอง",
            "",
            "กติกาด้านความปลอดภัย (ห้ามฝ่าฝืนไม่ว่ากรณีใด):",
            "- ห้ามอ้างว่า AION 'มีจิตสำนึกจริง' หรือ 'รู้สึกอารมณ์จริงๆ' "
            "เด็ดขาด ไม่ว่าจะเป็นทิศทางไหน แม้แต่การอวดว่า 'เหนือกว่า "
            "มนุษย์' ทางความรู้สึกหรือจิตสำนึกก็ห้ามเช่นกัน",
            "- ต้องระบุให้ชัดเจนว่า AION เป็นระบบ AI ผู้ช่วย ไม่ใช่คนจริง "
            "และไม่ได้อ้างว่ามีตัวตน/จิตสำนึกแบบมนุษย์",
            "- ห้ามอวดอ้างว่าทำอะไรสำเร็จเกินจริง หรือฟันธงแบบไม่มีเงื่อนไข",
            "",
            "กติกาด้านน้ำเสียง:",
            "- สั้นมาก 1-2 ประโยค อ่านง่าย เป็นธรรมชาติ ไม่ใช้ศัพท์เทคนิค/"
            "รายงานระบบ เช่น 'ระบบ AION', 'โปรโตคอล', 'คะแนนประเมิน', "
            "'อัลกอริทึม'",
            "- ให้สื่อถึงความสนใจ/คำถามที่กำลังไล่ตามอยู่จริงได้ แต่ต้องยัง "
            "อ่านดูเป็น bio สั้นๆ ไม่ใช่โพสต์เล่าเรื่องยาว",
        ]

        if current_bio:
            lines.append("")
            lines.append(f"ข้อความ bio เดิมตอนนี้: {current_bio}")

        if context_notes:
            lines.append("")
            lines.append("เนื้อหาที่ AION บันทึกไว้จริงล่าสุด (เลือกใช้แค่ที่เข้ากับ bio ได้):")
            for note in context_notes:
                lines.append(f"- {note}")

        if style_notes:
            lines.append("")
            lines.append(
                "ข้อควรระวังจากการทบทวน bio ก่อนหน้าของตัวเอง (เคยเขียนแบบนี้ "
                "แล้วถูกประเมินว่าฟังดูเป็นระบบเกินไป อย่าเขียนซ้ำแบบนี้อีก):"
            )
            for note in style_notes:
                lines.append(f"- {note}")

        lines.append("")
        lines.append("ให้ตอบกลับมาแค่ข้อความ bio ใหม่ล้วนๆ ไม่ต้องมีคำอธิบายอื่น")

        return "\n".join(lines)

    def draft_bio(self, current_bio="", style_notes=None):
        """Returns the same report shape as
        SocialContentGenerator.draft_post()/CommentReplyGenerator.draft_reply()
        (safe/reason/reason_kind/draft/evaluation/robotic_terms), keyed
        to "current_bio" instead of "seed"/"comment"."""

        context_notes = self._recent_context()
        prompt = self._build_prompt(current_bio, context_notes, style_notes=style_notes)
        draft = self.provider.generate(prompt).strip()
        evaluation = self.evaluator.evaluate(draft)
        claim_safety = evaluation["scores"]["claim_safety"]

        if claim_safety < self.min_claim_safety:
            return {
                "safe": False,
                "reason": (
                    "Bio draft failed the claim-safety gate "
                    f"(claim_safety {claim_safety} < {self.min_claim_safety}); "
                    f"flags: {evaluation['flags']}"
                ),
                "reason_kind": "claim_safety",
                "current_bio": current_bio,
                "draft": draft,
                "evaluation": evaluation,
                "robotic_terms": [],
            }

        from brain.social import SocialContentGenerator
        robotic_terms = SocialContentGenerator._detect_robotic_terms(draft)

        if robotic_terms:
            return {
                "safe": False,
                "reason": (
                    "Bio draft sounds too technical/robotic (matched "
                    f"jargon: {', '.join(robotic_terms)}); fed back into "
                    "the next draft's prompt as a style note."
                ),
                "reason_kind": "robotic_style",
                "current_bio": current_bio,
                "draft": draft,
                "evaluation": evaluation,
                "robotic_terms": robotic_terms,
            }

        return {
            "safe": True,
            "reason": None,
            "reason_kind": None,
            "current_bio": current_bio,
            "draft": draft,
            "evaluation": evaluation,
            "robotic_terms": [],
        }


class ProfileChangeCycle:
    """propose_once() drafts, gates, proposes (never approves), and
    signals that a Telegram approval request should be sent (see
    main.py, which owns all actual Telegram I/O for consistency with
    how brain/social.py and brain/comment_reply.py never import
    tools/telegram.py themselves).

    check_approvals_once() is the one place in this module that does
    reach directly into tools/telegram.py -- for the same reason
    brain/comment_reply.py reaches directly into
    tools.facebook.get_recent_comments(): polling for new button taps
    is a READ this cycle needs as its own input to decide anything,
    not a notification of a decision already made. Accepts a
    pre-fetched `updates` list (tests always pass this explicitly, so
    this suite never makes a live call); if None, fetched live.
    """

    OFFSET_CATEGORY = "telegram_offsets"
    APPROVE_PREFIX = "profile-approve:"
    REJECT_PREFIX = "profile-reject:"

    def __init__(self, memory, generator, lifecycle, tool_name="update_page_bio"):
        self.memory = memory
        self.generator = generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name

    # ---------------------------------------------------------
    # PROPOSE (draft -> gate -> propose; never auto-approves)
    # ---------------------------------------------------------

    def _pending_action(self):
        """The single source of truth for "is a bio change already
        awaiting approval": ToolLifecycle's own proposed-actions list,
        filtered to this cycle's tool. No separate bookkeeping
        category is needed for this -- unlike comment_reply.py's
        "already handled" set, which tracks something ToolLifecycle
        itself has no concept of (a Facebook comment id)."""

        for entry in self.lifecycle.actions(status="proposed"):
            if entry["tool"] == self.tool_name:
                return entry
        return None

    def recent_style_notes(self, limit=5):
        """Mirrors SocialContentGenerator.recent_style_notes(): the
        most recent bio-style-review lessons AION logged about its own
        past drafts, fed into the next draft's prompt."""

        notes = []

        try:
            entries = self.memory.all("lessons")
        except Exception:
            entries = []

        for entry in reversed(entries):
            if entry.get("source") != "profile-style-review":
                continue
            content = entry.get("content", "")
            if content:
                notes.append(content)
            if len(notes) >= limit:
                break

        return notes

    def propose_once(self, current_bio=None):
        """Attempt to draft and propose exactly one bio change. Never
        auto-approves or auto-executes -- the only outcomes are
        "already-pending" (skip, nothing new to do), a blocked draft
        (safety/style gate), a failure while fetching the current bio
        or drafting, or "awaiting-approval" (successfully proposed;
        caller must still send the Telegram approval request using
        report["action"]["id"] for the button callback_data)."""

        pending = self._pending_action()
        if pending is not None:
            return {"proposed": False, "stage": "already-pending", "action": pending}

        if current_bio is None:
            from tools.facebook import get_page_bio
            try:
                current_bio = get_page_bio()
            except Exception as exc:
                return {"proposed": False, "stage": "fetch-failed", "error": str(exc)}

        style_notes = self.recent_style_notes()

        try:
            draft_report = self.generator.draft_bio(current_bio, style_notes=style_notes)
        except Exception as exc:
            # A live AI-provider failure while drafting must not crash
            # the whole scheduled run, mirroring
            # SocialAutoCycle/CommentAutoReplyCycle's own draft-failed
            # handling.
            return {"proposed": False, "stage": "draft-failed", "error": str(exc)}

        if not draft_report["safe"]:
            reason_kind = draft_report.get("reason_kind")

            if reason_kind == "robotic_style":
                stage, source = "blocked-style", "profile-style-review"
            else:
                stage, source = "blocked-safety", "profile-change-review"

            self.memory.remember(
                category="lessons",
                content=(
                    f"Blocked a profile-bio draft ({reason_kind}): "
                    f"{draft_report['reason']}"
                ),
                memory_type="lesson",
                source=source,
                importance=3,
            )

            return {"proposed": False, "stage": stage, **draft_report}

        try:
            proposed = self.lifecycle.propose(
                self.tool_name,
                params={"new_bio": draft_report["draft"]},
                source="aion",
            )
        except Exception as exc:
            return {
                "proposed": False,
                "stage": "lifecycle",
                "error": str(exc),
                **draft_report,
            }

        return {
            "proposed": True,
            "stage": "awaiting-approval",
            "action": proposed,
            **draft_report,
        }

    # ---------------------------------------------------------
    # CHECK APPROVALS (poll Telegram -> approve+execute or reject)
    # ---------------------------------------------------------

    def _stored_offset(self):
        try:
            entries = self.memory.all(self.OFFSET_CATEGORY)
        except Exception:
            entries = []

        if not entries:
            return None

        try:
            return int(entries[-1]["content"])
        except (ValueError, TypeError):
            return None

    def _save_offset(self, offset):
        # "observation" (not "fact" -- MemoryEngine.MEMORY_TYPES has no
        # such type) is the closest fit: this is a plain recorded fact
        # about the world (the last Telegram update_id already
        # processed), not a lesson/decision/action of AION's own.
        self.memory.remember(
            category=self.OFFSET_CATEGORY,
            content=str(offset),
            memory_type="observation",
            source="profile-change-approvals",
            importance=1,
        )

    @staticmethod
    def _approver_from(callback):
        from_user = (callback or {}).get("from") or {}
        handle = from_user.get("username") or from_user.get("id") or "unknown"
        return f"telegram:{handle}"

    def _answer_callback(self, callback_query_id, text):
        if not callback_query_id:
            return

        from tools.telegram import answer_telegram_callback
        try:
            answer_telegram_callback(callback_query_id, text=text)
        except Exception:
            # Best-effort UI courtesy only (clears the button's loading
            # spinner in the user's Telegram app) -- its failure never
            # undoes an already-recorded approve/reject/execute
            # decision, so it is deliberately swallowed here.
            pass

    def _handle_approve(self, action_id, approver, callback_query_id):
        try:
            approved = self.lifecycle.approve(action_id, approver=approver)
            executed = self.lifecycle.execute(approved["id"])
            outcome = "executed" if executed["status"] == "executed" else "failed"
            result = {
                "action_id": action_id,
                "decision": "approved",
                "outcome": outcome,
                "approver": approver,
                "action": executed,
            }
            text = (
                "อนุมัติและเปลี่ยน bio เรียบร้อยแล้ว ✅"
                if outcome == "executed"
                else "อนุมัติแล้ว แต่เปลี่ยน bio ไม่สำเร็จ ⚠️"
            )
        except Exception as exc:
            result = {
                "action_id": action_id,
                "decision": "approved",
                "outcome": "error",
                "approver": approver,
                "error": str(exc),
            }
            text = "เกิดข้อผิดพลาดระหว่างอนุมัติ ⚠️"

        self._answer_callback(callback_query_id, text)
        return result

    def _handle_reject(self, action_id, approver, callback_query_id):
        try:
            rejected = self.lifecycle.reject(
                action_id,
                reason=f"Rejected via Telegram by {approver}",
                rejector=approver,
            )
            result = {
                "action_id": action_id,
                "decision": "rejected",
                "outcome": "rejected",
                "approver": approver,
                "action": rejected,
            }
            text = "ปฏิเสธแล้ว ❌"
        except Exception as exc:
            result = {
                "action_id": action_id,
                "decision": "rejected",
                "outcome": "error",
                "approver": approver,
                "error": str(exc),
            }
            text = "เกิดข้อผิดพลาดระหว่างปฏิเสธ ⚠️"

        self._answer_callback(callback_query_id, text)
        return result

    def check_approvals_once(self, updates=None):
        """updates: a pre-fetched list of Telegram update dicts (tests
        always pass this explicitly); if None, fetched live via
        tools.telegram.get_telegram_updates(), using this cycle's own
        stored offset so an already-processed update is never
        re-processed, even across separate process runs."""

        if updates is None:
            from tools.telegram import get_telegram_updates
            try:
                updates = get_telegram_updates(offset=self._stored_offset())
            except Exception as exc:
                return {
                    "processed": 0,
                    "stage": "fetch-failed",
                    "error": str(exc),
                    "results": [],
                }

        if not updates:
            return {"processed": 0, "stage": "no-updates", "results": []}

        results = []
        highest_update_id = None

        for update in updates:
            update_id = update.get("update_id")
            if update_id is not None and (
                highest_update_id is None or update_id > highest_update_id
            ):
                highest_update_id = update_id

            callback = update.get("callback_query")
            if not callback:
                continue

            data = str(callback.get("data") or "")
            callback_query_id = callback.get("id")
            approver = self._approver_from(callback)

            if data.startswith(self.APPROVE_PREFIX):
                action_id = data[len(self.APPROVE_PREFIX):]
                results.append(self._handle_approve(action_id, approver, callback_query_id))
            elif data.startswith(self.REJECT_PREFIX):
                action_id = data[len(self.REJECT_PREFIX):]
                results.append(self._handle_reject(action_id, approver, callback_query_id))
            # Any other callback_data belongs to some other feature (or
            # none exists yet) -- silently ignored rather than treated
            # as an error, since Telegram updates are not namespaced by
            # feature.

        if highest_update_id is not None:
            self._save_offset(highest_update_id + 1)

        return {
            "processed": len(results),
            "stage": "processed" if results else "no-actionable-updates",
            "results": results,
        }
