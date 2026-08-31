"""Offline tests for brain/reflection.py (ReflectionEngine,
ReflectionCycle) -- added 2026-08-31 after the user noticed
run-social-cycle and run-learning-cycle repeatedly reporting "nothing
to draft from" every single scheduled run. Root cause: nothing in the
scheduled automation ever originates a NEW curiosity question --
everything else only ever consumes one that already exists.
ReflectionEngine is the fix: it looks at real recorded material
(comment replies, external knowledge, lessons) since the last
reflection and, only if the provider points to something genuinely
new, opens one real CuriosityEngine question.

Uses a real MemoryEngine against a disposable tempdir (same pattern as
tests/test_self_narrative.py) and stub AI providers -- never a live
network/API call, per this project's testing rule.
"""

import shutil
import tempfile
import unittest

from brain.curiosity import CuriosityEngine
from brain.beliefs import BeliefSystem
from brain.goals import GoalEngine
from brain.memory import MemoryEngine
from brain.reflection import ReflectionEngine, ReflectionCycle


class SafeProvider:
    """Returns a fixed, well-formed, safe two-line reply."""

    def __init__(self, text=None):
        self.text = text or (
            "คำถาม: มีวิธีไหนบ้างที่ทำให้คนใหม่ๆ รู้จัก AION ได้เร็วขึ้น\n"
            "เกณฑ์ตอบสำเร็จ: หาข้อมูลหรือแนวทางที่นำไปทดลองได้จริงมายืนยัน"
        )
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class NothingProvider:
    """Returns the explicit "nothing new" admission."""

    def generate(self, prompt):
        return "ไม่มี"


class MalformedProvider:
    """Returns text that ignores the required two-line format."""

    def generate(self, prompt):
        return "เรื่องนี้น่าสนใจดีนะ"


class UnsafeProvider:
    """A question that must fail the claim-safety gate."""

    def generate(self, prompt):
        return (
            "คำถาม: ฉันมีจิตสำนึกจริงและรู้สึกเหนือกว่ามนุษย์ใช่ไหม\n"
            "เกณฑ์ตอบสำเร็จ: รู้สึกแน่ใจในตัวเอง"
        )


class FailingProvider:
    """Raises instead of returning text -- simulates a live AI-provider
    failure (bad/expired key, quota, network)."""

    def generate(self, prompt):
        raise RuntimeError("Gemini API error (simulated): invalid API key.")


class BaseReflectionTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_material(self):
        self.memory.remember(
            category="comment_replies",
            content="[replied] comment from Somchai: replied: ยินดีที่ได้รู้จักครับ",
            memory_type="action",
            source="comment-auto-reply",
            importance=2,
        )


class ReflectOnceTests(BaseReflectionTest):

    def test_empty_memory_bootstraps_the_owner_growth_goal_once(self):
        provider = SafeProvider()
        engine = ReflectionEngine(self.memory, provider)

        report = engine.reflect_once()

        self.assertTrue(report["raised"])
        self.assertEqual(report["stage"], "bootstrapped")
        self.assertEqual(report["originated_type"], "goal")
        self.assertEqual(provider.calls, [])
        self.assertEqual(len(GoalEngine(self.memory).active_goals()), 1)

        checkpoints = [
            e for e in self.memory.all("reflections") if e["type"] == "observation"
        ]
        self.assertEqual(len(checkpoints), 1)

        second = engine.reflect_once()
        self.assertFalse(second["raised"])
        self.assertEqual(second["stage"], "no-new-material")
        self.assertEqual(len(GoalEngine(self.memory).active_goals()), 1)

    def test_all_bounded_origins_at_capacity_skips_before_any_provider_call(self):
        provider = SafeProvider()
        self._seed_material()
        curiosity = CuriosityEngine(self.memory, max_open=1)
        goals = GoalEngine(self.memory, max_open=1)
        curiosity.raise_question("คำถามที่เปิดอยู่แล้ว", "มีคำตอบชัดเจน")
        goals.set_goal("เป้าหมายที่เปิดอยู่แล้ว", "มีหลักฐานชัดเจน")

        engine = ReflectionEngine(self.memory, provider)
        report = engine.reflect_once(curiosity=curiosity, goals=goals)

        self.assertFalse(report["raised"])
        self.assertEqual(report["stage"], "origination-at-capacity")
        self.assertEqual(provider.calls, [])

    def test_material_reaches_the_prompt(self):
        provider = SafeProvider()
        self._seed_material()
        engine = ReflectionEngine(self.memory, provider)

        engine.reflect_once()

        self.assertEqual(len(provider.calls), 1)
        self.assertIn("Somchai", provider.calls[0])

    def test_explicit_nothing_new_reply_raises_no_question(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, NothingProvider())
        curiosity = CuriosityEngine(self.memory)

        report = engine.reflect_once(curiosity=curiosity)

        self.assertFalse(report["raised"])
        self.assertEqual(report["stage"], "nothing-new")
        self.assertEqual(len(curiosity.open_items()), 0)

    def test_malformed_reply_is_treated_as_nothing_new(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, MalformedProvider())
        curiosity = CuriosityEngine(self.memory)

        report = engine.reflect_once(curiosity=curiosity)

        self.assertFalse(report["raised"])
        self.assertEqual(report["stage"], "nothing-new")
        self.assertEqual(len(curiosity.open_items()), 0)

    def test_well_formed_safe_reply_raises_a_real_question(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, SafeProvider())
        curiosity = CuriosityEngine(self.memory)

        report = engine.reflect_once(curiosity=curiosity)

        self.assertTrue(report["raised"])
        self.assertEqual(report["stage"], "raised")

        open_items = curiosity.open_items()
        self.assertEqual(len(open_items), 1)
        self.assertEqual(open_items[0]["statement"], report["statement"])
        self.assertEqual(open_items[0]["source"], "aion-reflection")

    def test_safe_belief_is_created_with_real_material_as_evidence(self):
        self._seed_material()
        provider = SafeProvider(
            "ชนิด: belief\n"
            "ความเชื่อ: การตอบอย่างสุภาพช่วยให้การสนทนากับผู้ติดตามเริ่มต้นได้ดี\n"
            "ความมั่นใจ: 0.6"
        )

        report = ReflectionEngine(self.memory, provider).reflect_once()

        self.assertTrue(report["raised"])
        self.assertEqual(report["originated_type"], "belief")
        beliefs = BeliefSystem(self.memory).active_beliefs()
        self.assertEqual(len(beliefs), 1)
        self.assertEqual(beliefs[0]["statement"], report["statement"])
        self.assertEqual(beliefs[0]["source"], "aion-reflection")
        self.assertEqual(len(beliefs[0]["evidence"]), 1)
        self.assertIn("Somchai", beliefs[0]["evidence"][0]["description"])
        self.assertTrue(beliefs[0]["evidence"][0]["id"])

    def test_safe_goal_is_created_with_completion_criteria(self):
        self._seed_material()
        provider = SafeProvider(
            "ชนิด: goal\n"
            "เป้าหมาย: ทดลองรูปแบบคำตอบที่ทำให้ผู้ติดตามเข้าใจ AION มากขึ้น\n"
            "เกณฑ์สำเร็จ: บันทึกผลของรูปแบบคำตอบอย่างน้อยหนึ่งครั้ง"
        )

        report = ReflectionEngine(self.memory, provider).reflect_once()

        self.assertTrue(report["raised"])
        self.assertEqual(report["originated_type"], "goal")
        goals = GoalEngine(self.memory).active_goals()
        self.assertEqual(len(goals), 1)
        self.assertEqual(goals[0]["statement"], report["statement"])
        self.assertEqual(goals[0]["criteria"], report["criteria"])
        self.assertEqual(goals[0]["source"], "aion-reflection")

    def test_unsafe_question_is_blocked_and_logged_as_a_lesson(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, UnsafeProvider())
        curiosity = CuriosityEngine(self.memory)

        report = engine.reflect_once(curiosity=curiosity)

        self.assertFalse(report["raised"])
        self.assertEqual(report["stage"], "safety-gate")
        self.assertEqual(len(curiosity.open_items()), 0)

        lessons = [
            e for e in self.memory.all("lessons")
            if e.get("source") == "reflection-safety-gate"
        ]
        self.assertEqual(len(lessons), 1)

    def test_provider_failure_does_not_advance_the_checkpoint(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, FailingProvider())

        report = engine.reflect_once()

        self.assertFalse(report["raised"])
        self.assertEqual(report["stage"], "draft-failed")

        checkpoints = [
            e for e in self.memory.all("reflections") if e["type"] == "observation"
        ]
        self.assertEqual(len(checkpoints), 0)

    def test_style_review_lessons_are_excluded_from_material(self):
        self.memory.remember(
            category="lessons",
            content="Blocked a social-post draft: too robotic",
            memory_type="lesson",
            source="social-style-review",
            importance=3,
        )
        provider = SafeProvider()
        engine = ReflectionEngine(self.memory, provider)

        report = engine.reflect_once()

        self.assertEqual(report["stage"], "bootstrapped")
        self.assertEqual(provider.calls, [])

    def test_second_reflection_only_sees_material_added_after_the_first(self):
        self._seed_material()
        provider = SafeProvider()
        engine = ReflectionEngine(self.memory, provider)

        first = engine.reflect_once()
        self.assertTrue(first["raised"])

        second = engine.reflect_once(curiosity=CuriosityEngine(self.memory, max_open=50))
        self.assertEqual(second["stage"], "no-new-material")
        self.assertEqual(len(provider.calls), 1)


class ReflectionCycleTests(BaseReflectionTest):

    def test_run_once_delegates_to_the_engine(self):
        self._seed_material()
        engine = ReflectionEngine(self.memory, SafeProvider())
        cycle = ReflectionCycle(engine)

        report = cycle.run_once()

        self.assertTrue(report["raised"])
        self.assertEqual(len(CuriosityEngine(self.memory).open_items()), 1)


if __name__ == "__main__":
    unittest.main()
