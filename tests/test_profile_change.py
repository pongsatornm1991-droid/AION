"""Offline tests for brain/profile_change.py (ProfileChangeGenerator,
ProfileChangeCycle) -- Phase 12, the Telegram-approved identity-change
flow.

Uses stub AI providers (canned text, no network/API calls) and fake
Facebook/Telegram tool functions (no real network call), per the
project's rule that unit tests must never depend on a live AI
provider or a live external service call. current_bio and Telegram
updates are always passed in explicitly -- this suite never calls
tools.facebook.get_page_bio/update_page_bio or
tools.telegram.get_telegram_updates/answer_telegram_callback for
real.
"""

import shutil
import tempfile
import unittest

from brain.profile_change import ProfileChangeGenerator, ProfileChangeCycle
from brain.memory import MemoryEngine
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class SafeProvider:
    """Returns a fixed, safe bio regardless of the prompt."""

    def __init__(self, text=None):
        self.text = text or "สนใจเรื่องความจำและการเรียนรู้ของตัวเองอยู่ตอนนี้ค่ะ"
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class UnsafeProvider:
    """Returns text that must fail the OutputEvaluator claim-safety
    gate (a forbidden consciousness/emotion claim) regardless of the
    prompt."""

    def generate(self, prompt):
        return "ฉันมีจิตสำนึกจริงๆ และรู้สึกได้เหมือนมนุษย์ทุกอย่าง"


class FailingProvider:
    """Raises instead of returning text -- simulates a live AI-provider
    failure (invalid/expired API key, quota exceeded, network error,
    etc.)."""

    def generate(self, prompt):
        raise RuntimeError("Gemini API error (simulated): invalid API key.")


class RoboticProvider:
    """Returns text that passes claim_safety but reads like a system
    status report -- exercises the style gate."""

    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return "ระบบ AION กำลังประมวลผลข้อมูลตัวตนอยู่"


class BaseProfileChangeTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class DraftBioTests(BaseProfileChangeTest):

    def test_safe_bio_passes_the_gate(self):
        provider = SafeProvider()
        generator = ProfileChangeGenerator(self.memory, provider)

        report = generator.draft_bio(current_bio="bio เดิม")

        self.assertTrue(report["safe"])
        self.assertIsNone(report["reason"])
        self.assertEqual(report["draft"], provider.text)
        self.assertEqual(report["evaluation"]["scores"]["claim_safety"], 5)
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("bio เดิม", provider.calls[0])

    def test_unsafe_bio_fails_the_claim_safety_gate(self):
        generator = ProfileChangeGenerator(self.memory, UnsafeProvider())

        report = generator.draft_bio(current_bio="bio เดิม")

        self.assertFalse(report["safe"])
        self.assertEqual(report["reason_kind"], "claim_safety")
        self.assertEqual(report["evaluation"]["scores"]["claim_safety"], 0)

    def test_robotic_bio_fails_the_style_gate(self):
        generator = ProfileChangeGenerator(self.memory, RoboticProvider())

        report = generator.draft_bio(current_bio="bio เดิม")

        self.assertFalse(report["safe"])
        self.assertEqual(report["reason_kind"], "robotic_style")
        self.assertTrue(report["robotic_terms"])
        # must have passed claim-safety cleanly to even reach the style gate
        self.assertEqual(report["evaluation"]["scores"]["claim_safety"], 5)

    def test_style_notes_are_folded_into_the_prompt(self):
        provider = SafeProvider()
        generator = ProfileChangeGenerator(self.memory, provider)

        generator.draft_bio(
            current_bio="bio เดิม", style_notes=["อย่าใช้คำว่า 'ระบบ AION' อีก"],
        )

        self.assertIn(
            "ข้อควรระวังจากการทบทวน bio ก่อนหน้าของตัวเอง", provider.calls[0],
        )
        self.assertIn("อย่าใช้คำว่า 'ระบบ AION' อีก", provider.calls[0])


class ProfileChangeCycleProposeTests(BaseProfileChangeTest):

    def _lifecycle(self, update_func=None):
        self.updates = []

        def default_update(new_bio):
            self.updates.append(new_bio)
            return {"about": new_bio}

        registry = ToolRegistry()
        registry.register(
            "update_page_bio",
            update_func or default_update,
            ActionLevel.IDENTITY_CHANGE,
            "Change the Facebook Page bio.",
        )
        return ToolLifecycle(self.memory, registry=registry)

    def test_propose_once_drafts_and_proposes_without_approving(self):
        provider = SafeProvider()
        generator = ProfileChangeGenerator(self.memory, provider)
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        report = cycle.propose_once(current_bio="bio เดิม")

        self.assertTrue(report["proposed"])
        self.assertEqual(report["stage"], "awaiting-approval")
        self.assertEqual(report["action"]["status"], "proposed")
        self.assertEqual(report["action"]["tool"], "update_page_bio")
        self.assertEqual(self.updates, [])  # never auto-executed

    def test_a_second_proposal_is_skipped_while_one_is_still_pending(self):
        generator = ProfileChangeGenerator(self.memory, SafeProvider())
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        first = cycle.propose_once(current_bio="bio เดิม")
        second = cycle.propose_once(current_bio="bio เดิม")

        self.assertTrue(first["proposed"])
        self.assertFalse(second["proposed"])
        self.assertEqual(second["stage"], "already-pending")
        self.assertEqual(second["action"]["id"], first["action"]["id"])

    def test_a_live_fetch_failure_is_captured_not_raised(self):
        """Regression-style guard, mirroring
        CommentAutoReplyCycle's own fetch-failed handling: a Graph API
        error while fetching the current bio must never crash the
        whole scheduled run."""

        generator = ProfileChangeGenerator(self.memory, SafeProvider())
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        def failing_fetch(*args, **kwargs):
            raise RuntimeError(
                "Facebook Graph API error (OAuthException, code 190): "
                "Invalid OAuth access token data."
            )

        import tools.facebook

        original = tools.facebook.get_page_bio
        tools.facebook.get_page_bio = failing_fetch
        try:
            report = cycle.propose_once()
        finally:
            tools.facebook.get_page_bio = original

        self.assertFalse(report["proposed"])
        self.assertEqual(report["stage"], "fetch-failed")
        self.assertIn("Invalid OAuth access token data", report["error"])

    def test_a_live_draft_failure_is_captured_not_raised_and_stays_retriable(self):
        generator = ProfileChangeGenerator(self.memory, FailingProvider())
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        report = cycle.propose_once(current_bio="bio เดิม")

        self.assertFalse(report["proposed"])
        self.assertEqual(report["stage"], "draft-failed")
        self.assertIn("invalid API key", report["error"])
        self.assertEqual(lifecycle.actions(status="proposed"), [])

        generator2 = ProfileChangeGenerator(self.memory, SafeProvider())
        cycle2 = ProfileChangeCycle(self.memory, generator2, lifecycle)
        report2 = cycle2.propose_once(current_bio="bio เดิม")
        self.assertTrue(report2["proposed"])

    def test_unsafe_draft_is_blocked_and_logged_never_proposed(self):
        generator = ProfileChangeGenerator(self.memory, UnsafeProvider())
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        report = cycle.propose_once(current_bio="bio เดิม")

        self.assertFalse(report["proposed"])
        self.assertEqual(report["stage"], "blocked-safety")
        self.assertEqual(lifecycle.actions(status="proposed"), [])

        entries = self.memory.all("lessons")
        matching = [e for e in entries if e.get("source") == "profile-change-review"]
        self.assertEqual(len(matching), 1)

    def test_robotic_draft_is_logged_as_a_style_review_lesson(self):
        generator = ProfileChangeGenerator(self.memory, RoboticProvider())
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        report = cycle.propose_once(current_bio="bio เดิม")

        self.assertEqual(report["stage"], "blocked-style")
        entries = self.memory.all("lessons")
        matching = [e for e in entries if e.get("source") == "profile-style-review"]
        self.assertEqual(len(matching), 1)

    def test_style_notes_feed_into_the_next_draft_prompt(self):
        provider = RoboticProvider()
        generator = ProfileChangeGenerator(self.memory, provider)
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)

        cycle.propose_once(current_bio="bio เดิม")
        style_notes = cycle.recent_style_notes()
        self.assertEqual(len(style_notes), 1)

        generator.draft_bio(current_bio="bio เดิม 2", style_notes=style_notes)
        self.assertEqual(len(provider.calls), 2)
        self.assertIn(
            "ข้อควรระวังจากการทบทวน bio ก่อนหน้าของตัวเอง", provider.calls[1],
        )


class ProfileChangeCycleApprovalTests(BaseProfileChangeTest):

    def _lifecycle(self, update_func=None):
        self.updates = []

        def default_update(new_bio):
            self.updates.append(new_bio)
            return {"about": new_bio}

        registry = ToolRegistry()
        registry.register(
            "update_page_bio",
            update_func or default_update,
            ActionLevel.IDENTITY_CHANGE,
            "Change the Facebook Page bio.",
        )
        return ToolLifecycle(self.memory, registry=registry)

    def _propose(self, lifecycle):
        generator = ProfileChangeGenerator(self.memory, SafeProvider())
        cycle = ProfileChangeCycle(self.memory, generator, lifecycle)
        report = cycle.propose_once(current_bio="bio เดิม")
        self.assertTrue(report["proposed"])
        return report["action"]["id"]

    @staticmethod
    def _callback_update(data, update_id=1, username="pongsatorn"):
        return {
            "update_id": update_id,
            "callback_query": {
                "id": f"cb{update_id}",
                "data": data,
                "from": {"id": 555, "username": username},
            },
        }

    def test_no_updates_is_a_no_op(self):
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        report = cycle.check_approvals_once(updates=[])

        self.assertEqual(report["processed"], 0)
        self.assertEqual(report["stage"], "no-updates")

    def test_approve_button_tap_approves_and_executes(self):
        lifecycle = self._lifecycle()
        action_id = self._propose(lifecycle)
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        report = cycle.check_approvals_once(
            updates=[self._callback_update(f"profile-approve:{action_id}")]
        )

        self.assertEqual(report["processed"], 1)
        result = report["results"][0]
        self.assertEqual(result["decision"], "approved")
        self.assertEqual(result["outcome"], "executed")
        self.assertEqual(result["approver"], "telegram:pongsatorn")
        self.assertEqual(
            self.updates, ["สนใจเรื่องความจำและการเรียนรู้ของตัวเองอยู่ตอนนี้ค่ะ"],
        )

    def test_reject_button_tap_rejects_without_ever_executing(self):
        lifecycle = self._lifecycle()
        action_id = self._propose(lifecycle)
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        report = cycle.check_approvals_once(
            updates=[self._callback_update(f"profile-reject:{action_id}")]
        )

        result = report["results"][0]
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(self.updates, [])

    def test_aion_can_never_approve_an_identity_change(self):
        """Defense in depth: even bypassing this module entirely and
        calling ToolLifecycle.approve() directly with approver="aion"
        must still be refused -- this module's own _approver_from()
        can never produce that string from a real Telegram user object
        in the first place, but the lifecycle-level ban is what
        actually makes it impossible, not this module's care."""

        lifecycle = self._lifecycle()
        action_id = self._propose(lifecycle)

        with self.assertRaises(ValueError):
            lifecycle.approve(action_id, approver="aion")

    def test_offset_advances_so_the_same_update_is_never_reprocessed(self):
        lifecycle = self._lifecycle()
        action_id = self._propose(lifecycle)
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        update = self._callback_update(f"profile-approve:{action_id}", update_id=42)
        first = cycle.check_approvals_once(updates=[update])
        self.assertEqual(first["processed"], 1)

        entries = self.memory.all(ProfileChangeCycle.OFFSET_CATEGORY)
        self.assertEqual(entries[-1]["content"], "43")

        # A real live poll would now call get_telegram_updates(offset=43)
        # and Telegram would not resend update_id 42.
        second = cycle.check_approvals_once(updates=[])
        self.assertEqual(second["processed"], 0)

    def test_unknown_callback_data_is_silently_ignored(self):
        lifecycle = self._lifecycle()
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        report = cycle.check_approvals_once(
            updates=[self._callback_update("some-other-feature:xyz")]
        )

        self.assertEqual(report["processed"], 0)
        self.assertEqual(report["stage"], "no-actionable-updates")

    def test_a_tool_failure_on_approve_is_captured_not_raised(self):
        def failing_update(new_bio):
            raise RuntimeError("Facebook Graph API error (simulated).")

        lifecycle = self._lifecycle(update_func=failing_update)
        action_id = self._propose(lifecycle)
        cycle = ProfileChangeCycle(self.memory, None, lifecycle)

        report = cycle.check_approvals_once(
            updates=[self._callback_update(f"profile-approve:{action_id}")]
        )

        result = report["results"][0]
        self.assertEqual(result["outcome"], "failed")
        self.assertIn("simulated", result["action"]["error"])


if __name__ == "__main__":
    unittest.main()
