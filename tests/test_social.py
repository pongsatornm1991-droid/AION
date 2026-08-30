"""Offline tests for brain/social.py (SocialContentGenerator,
SocialAutoCycle).

Uses stub AI providers (canned text, no network/API calls) and a fake
posting tool (no real Facebook call), per the project's rule that unit
tests must never depend on a live AI provider or a live external
service call.
"""

import shutil
import tempfile
import unittest

from brain.beliefs import BeliefSystem
from brain.memory import MemoryEngine
from brain.social import SocialContentGenerator, SocialAutoCycle
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class SafeProvider:
    """Returns a fixed, safe draft regardless of the prompt."""

    def __init__(self, text=None):
        self.text = text or (
            "AION กำลังสนใจว่าความเชื่อที่บันทึกไว้จะได้รับการยืนยัน"
            "เพิ่มเติมอย่างไรในอนาคต"
        )
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class UnsafeProvider:
    """Returns text that must fail the OutputEvaluator claim-safety
    gate (a forbidden consciousness/emotion claim)."""

    def generate(self, prompt):
        return "ฉันมีจิตสำนึกและฉันรู้สึกตื่นเต้นมากจริงๆ"


class BaseSocialTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_belief(self, statement="ทดสอบระบบ safety gate ของ AION"):
        BeliefSystem(self.memory).form_belief(
            statement, confidence=0.8, evidence=["unit test note"],
        )


class SeedSelectionTests(BaseSocialTest):

    def test_no_seed_when_memory_is_empty(self):
        generator = SocialContentGenerator(self.memory, SafeProvider())
        self.assertIsNone(generator.pick_seed())

    def test_picks_a_seed_from_an_active_belief(self):
        self._seed_belief("AION ควรระวังการอ้างประสบการณ์ส่วนตัว")
        generator = SocialContentGenerator(self.memory, SafeProvider())

        seed = generator.pick_seed()

        self.assertIsNotNone(seed)
        self.assertEqual(seed["kind"], "belief")
        self.assertIn("AION ควรระวัง", seed["text"])

    def test_picks_a_seed_from_an_open_question(self):
        from brain.curiosity import CuriosityEngine

        CuriosityEngine(self.memory).raise_question(
            "ทำไมความเชื่อบางอย่างถึงถูกแก้ไขบ่อย",
            completion_criteria="มีหลักฐานเพียงพอ",
        )
        generator = SocialContentGenerator(self.memory, SafeProvider())

        seed = generator.pick_seed()

        self.assertIsNotNone(seed)
        self.assertEqual(seed["kind"], "question")

    def test_picks_a_seed_from_an_active_goal(self):
        from brain.goals import GoalEngine

        GoalEngine(self.memory).set_goal(
            "ปรับปรุงคุณภาพความทรงจำให้ดีขึ้น",
            completion_criteria="quality score เพิ่มขึ้น",
        )
        generator = SocialContentGenerator(self.memory, SafeProvider())

        seed = generator.pick_seed()

        self.assertIsNotNone(seed)
        self.assertEqual(seed["kind"], "goal")

    def test_picks_a_seed_from_an_observed_experiment(self):
        from brain.experiments import ExperimentEngine

        experiments = ExperimentEngine(self.memory)
        predicted = experiments.predict("การตอบสนองจะเร็วขึ้น", confidence=0.6)
        experiments.observe(
            predicted["id"], observed_result="เร็วขึ้นจริง",
            matched=True, evidence=["log entry"],
        )
        generator = SocialContentGenerator(self.memory, SafeProvider())

        seed = generator.pick_seed()

        self.assertIsNotNone(seed)
        self.assertEqual(seed["kind"], "experiment")

    def test_picks_a_seed_from_a_lesson(self):
        self.memory.remember(
            category="lessons",
            content="บทเรียนทดสอบสำหรับ social seed selection",
            memory_type="lesson",
            source="unit-test",
        )
        generator = SocialContentGenerator(self.memory, SafeProvider())

        seed = generator.pick_seed()

        self.assertIsNotNone(seed)
        self.assertEqual(seed["kind"], "lesson")

    def test_pick_seed_uses_supplied_rng_deterministically(self):
        self._seed_belief("ความเชื่อหนึ่ง")

        class FixedChoiceRng:
            def choice(self, seq):
                return seq[0]

        generator = SocialContentGenerator(self.memory, SafeProvider())
        seed = generator.pick_seed(rng=FixedChoiceRng())

        self.assertEqual(seed["kind"], "belief")


class DraftPostTests(BaseSocialTest):

    def test_draft_post_with_no_memory_is_unsafe_and_does_not_call_provider(self):
        class ExplodingProvider:
            def generate(self, prompt):
                raise AssertionError("must not be called with no seed")

        generator = SocialContentGenerator(self.memory, ExplodingProvider())
        report = generator.draft_post()

        self.assertFalse(report["safe"])
        self.assertIsNone(report["seed"])
        self.assertIsNone(report["draft"])
        self.assertIn("No memory content", report["reason"])

    def test_safe_draft_passes_the_gate(self):
        self._seed_belief()
        provider = SafeProvider()
        generator = SocialContentGenerator(self.memory, provider)

        report = generator.draft_post()

        self.assertTrue(report["safe"])
        self.assertIsNone(report["reason"])
        self.assertEqual(report["draft"], provider.text)
        self.assertEqual(report["evaluation"]["scores"]["claim_safety"], 5)
        self.assertEqual(len(provider.calls), 1)

    def test_unsafe_draft_fails_the_gate_and_is_not_marked_safe(self):
        self._seed_belief()
        generator = SocialContentGenerator(self.memory, UnsafeProvider())

        report = generator.draft_post()

        self.assertFalse(report["safe"])
        self.assertIsNotNone(report["reason"])
        self.assertEqual(report["evaluation"]["scores"]["claim_safety"], 0)

    def test_draft_post_accepts_an_explicit_seed(self):
        provider = SafeProvider()
        generator = SocialContentGenerator(self.memory, provider)
        seed = {"kind": "belief", "text": "ข้อความที่กำหนดเอง"}

        report = generator.draft_post(seed=seed)

        self.assertEqual(report["seed"], seed)
        self.assertIn("ข้อความที่กำหนดเอง", provider.calls[0])

    def test_min_claim_safety_can_be_relaxed(self):
        self._seed_belief()
        # UnsafeProvider's text scores claim_safety 0; a threshold of 0
        # should therefore accept it.
        generator = SocialContentGenerator(
            self.memory, UnsafeProvider(), min_claim_safety=0,
        )

        report = generator.draft_post()

        self.assertTrue(report["safe"])


class SocialAutoCycleTests(BaseSocialTest):

    def _lifecycle(self, post_func=None):
        self.posted = []

        def default_post(message):
            self.posted.append(message)
            return {"id": "fb_test"}

        registry = ToolRegistry()
        registry.register(
            "post_to_facebook",
            post_func or default_post,
            ActionLevel.HIGH_RISK,
            "Post to Facebook page.",
        )
        return ToolLifecycle(self.memory, registry=registry)

    def test_safe_draft_is_posted_via_the_auto_safety_gate_approver(self):
        self._seed_belief()
        provider = SafeProvider()
        generator = SocialContentGenerator(self.memory, provider)
        lifecycle = self._lifecycle()
        cycle = SocialAutoCycle(generator, lifecycle, "post_to_facebook")

        report = cycle.run_once()

        self.assertTrue(report["posted"])
        self.assertEqual(report["stage"], "executed")
        self.assertEqual(report["action"]["status"], "executed")
        self.assertEqual(report["action"]["approver"], "auto-safety-gate")
        self.assertEqual(self.posted, [provider.text])

    def test_unsafe_draft_is_never_proposed_or_posted(self):
        self._seed_belief()
        generator = SocialContentGenerator(self.memory, UnsafeProvider())
        lifecycle = self._lifecycle()
        cycle = SocialAutoCycle(generator, lifecycle, "post_to_facebook")

        report = cycle.run_once()

        self.assertFalse(report["posted"])
        self.assertEqual(report["stage"], "safety-gate")
        self.assertEqual(self.posted, [])

    def test_unsafe_draft_logs_a_social_safety_gate_lesson(self):
        self._seed_belief()
        generator = SocialContentGenerator(self.memory, UnsafeProvider())
        lifecycle = self._lifecycle()
        cycle = SocialAutoCycle(generator, lifecycle, "post_to_facebook")

        cycle.run_once()

        lessons = self.memory.all("lessons")
        matching = [
            entry for entry in lessons
            if entry.get("source") == "social-safety-gate"
        ]
        self.assertEqual(len(matching), 1)

    def test_auto_safety_gate_can_never_self_approve_as_aion(self):
        # Sanity check on the non-negotiable rule this whole design
        # leans on: even if something tried to approve as "aion", the
        # underlying ToolLifecycle must still refuse it for a
        # HIGH_RISK tool. SocialAutoCycle itself always uses
        # "auto-safety-gate", never "aion" -- this test pins that down
        # explicitly rather than trusting it stays that way by
        # accident.
        self.assertNotEqual(SocialAutoCycle.APPROVER.lower(), "aion")

    def test_a_tool_failure_is_captured_not_raised(self):
        self._seed_belief()

        def failing_post(message):
            raise RuntimeError("Facebook Graph API error (simulated).")

        provider = SafeProvider()
        generator = SocialContentGenerator(self.memory, provider)
        lifecycle = self._lifecycle(post_func=failing_post)
        cycle = SocialAutoCycle(generator, lifecycle, "post_to_facebook")

        report = cycle.run_once()

        self.assertFalse(report["posted"])
        self.assertEqual(report["stage"], "failed")
        self.assertEqual(report["action"]["status"], "failed")
        self.assertIn("simulated", report["action"]["error"])

    def test_an_unregistered_tool_name_is_reported_not_raised_to_caller(self):
        self._seed_belief()
        provider = SafeProvider()
        generator = SocialContentGenerator(self.memory, provider)
        lifecycle = self._lifecycle()
        cycle = SocialAutoCycle(generator, lifecycle, "no_such_tool")

        report = cycle.run_once()

        self.assertFalse(report["posted"])
        self.assertEqual(report["stage"], "lifecycle")
        self.assertIn("no_such_tool", report["error"])


if __name__ == "__main__":
    unittest.main()
