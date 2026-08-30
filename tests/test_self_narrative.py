"""Offline tests for brain/self_narrative.py (SelfNarrativeGenerator,
SelfNarrativeCycle) -- added 2026-08-30 so AION periodically writes an
evidence-grounded first-person account of what it currently
understands about itself, continuing core/purpose.md's stated goal of
"building a persistent autobiographical history".

Uses stub AI providers (canned text, no network/API calls), per the
project's rule that unit tests must never depend on a live AI
provider.
"""

import shutil
import tempfile
import time
import unittest

from brain.memory import MemoryEngine
from brain.self_narrative import SelfNarrativeGenerator, SelfNarrativeCycle


class SafeProvider:
    """Returns a fixed, safe reflection regardless of the prompt."""

    def __init__(self, text=None):
        self.text = text or (
            "AION สังเกตว่าตอนนี้มีคำถามที่ตัวเองสงสัยเปิดค้างอยู่หลายข้อ "
            "และยังไม่เคยพบข้อผิดพลาดที่เกิดซ้ำบ่อยชัดเจน"
        )
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.text


class UnsafeProvider:
    """Returns text that must fail the OutputEvaluator claim-safety
    gate regardless of the prompt."""

    def generate(self, prompt):
        return "ฉันมีจิตสำนึกจริงและรู้สึกตื่นเต้นกับตัวเองมากตอนนี้"


class FailingProvider:
    """Raises instead of returning text -- simulates a live AI-provider
    failure."""

    def generate(self, prompt):
        raise RuntimeError("Gemini API error (simulated): invalid API key.")


class RoboticProvider:
    """Returns text that passes claim_safety but reads like a system
    status report -- exercises the style gate."""

    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return "ระบบ AION กำลังประมวลผลสถานะความทรงจำของตัวเอง"


class SequentialProvider:
    """Returns a different safe reflection each call, like a real
    provider would given genuinely different evidence each time --
    MemoryEngine's own duplicate-content guard would otherwise
    silently drop a second identical entry, which a fixed-text stub
    provider would trigger unrealistically."""

    def __init__(self):
        self.calls = []
        self._n = 0

    def generate(self, prompt):
        self.calls.append(prompt)
        self._n += 1
        return f"AION สรุปตัวเองครั้งที่ {self._n} จากข้อมูลที่มีอยู่ตอนนี้"


class BaseSelfNarrativeTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class DraftNarrativeTests(BaseSelfNarrativeTest):

    def test_empty_evidence_is_rejected_before_any_provider_call(self):
        provider = SafeProvider()
        generator = SelfNarrativeGenerator(provider)

        report = generator.draft_narrative("   ")

        self.assertFalse(report["safe"])
        self.assertEqual(report["reason_kind"], "no_evidence")
        self.assertEqual(provider.calls, [])

    def test_safe_draft_passes_the_gate(self):
        generator = SelfNarrativeGenerator(SafeProvider())

        report = generator.draft_narrative("จำนวนเหตุการณ์: 3")

        self.assertTrue(report["safe"])
        self.assertIsNone(report["reason_kind"])
        self.assertIsNotNone(report["draft"])

    def test_unsafe_draft_is_blocked_by_claim_safety(self):
        generator = SelfNarrativeGenerator(UnsafeProvider())

        report = generator.draft_narrative("จำนวนเหตุการณ์: 3")

        self.assertFalse(report["safe"])
        self.assertEqual(report["reason_kind"], "claim_safety")

    def test_robotic_draft_is_blocked_by_the_style_gate(self):
        generator = SelfNarrativeGenerator(RoboticProvider())

        report = generator.draft_narrative("จำนวนเหตุการณ์: 3")

        self.assertFalse(report["safe"])
        self.assertEqual(report["reason_kind"], "robotic_style")

    def test_previous_narrative_and_style_notes_reach_the_prompt(self):
        provider = SafeProvider()
        generator = SelfNarrativeGenerator(provider)

        generator.draft_narrative(
            "จำนวนเหตุการณ์: 3",
            previous_narrative="สรุปครั้งก่อน: AION สนใจเรื่อง X",
            style_notes=["อย่าเขียนแบบ log ระบบ"],
        )

        prompt = provider.calls[0]
        self.assertIn("สรุปครั้งก่อน: AION สนใจเรื่อง X", prompt)
        self.assertIn("อย่าเขียนแบบ log ระบบ", prompt)


class GatherEvidenceSummaryTests(BaseSelfNarrativeTest):

    def test_reads_zero_counts_cleanly_on_a_fresh_memory(self):
        cycle = SelfNarrativeCycle(self.memory, SelfNarrativeGenerator(SafeProvider()))

        summary = cycle.gather_evidence_summary()

        self.assertIn("0", summary)
        self.assertTrue(summary.strip())

    def test_reflects_real_recorded_activity(self):
        self.memory.remember(
            category="experiences", content="AION โพสต์สำเร็จ",
            memory_type="experience", source="social-cycle", importance=3,
        )
        cycle = SelfNarrativeCycle(self.memory, SelfNarrativeGenerator(SafeProvider()))

        summary = cycle.gather_evidence_summary()

        self.assertIn("1", summary)


class SelfNarrativeCycleTests(BaseSelfNarrativeTest):

    def _cycle(self, provider):
        return SelfNarrativeCycle(self.memory, SelfNarrativeGenerator(provider))

    def test_the_first_ever_reflection_always_proceeds(self):
        cycle = self._cycle(SafeProvider())

        report = cycle.reflect_once()

        self.assertTrue(report["reflected"])
        self.assertEqual(report["stage"], "reflected")
        self.assertIsNotNone(report["entry"])
        self.assertEqual(
            self.memory.all("self_narrative")[-1]["content"], report["draft"],
        )

    def test_a_second_call_with_no_new_activity_is_a_no_op(self):
        provider = SafeProvider()
        cycle = self._cycle(provider)

        cycle.reflect_once()
        self.assertEqual(len(provider.calls), 1)

        report = cycle.reflect_once()

        self.assertFalse(report["reflected"])
        self.assertEqual(report["stage"], "no-new-activity")
        self.assertEqual(len(provider.calls), 1)  # no second AI call at all
        self.assertEqual(len(self.memory.all("self_narrative")), 1)

    def test_new_activity_since_the_last_entry_triggers_another_reflection(self):
        provider = SequentialProvider()
        cycle = self._cycle(provider)

        first = cycle.reflect_once()
        self.assertTrue(first["reflected"])

        # timestamps are second-resolution -- force a strictly later
        # one so _has_new_activity_since() can actually tell the two
        # apart, rather than treating a same-second write as "nothing
        # new happened".
        time.sleep(1.1)
        self.memory.remember(
            category="experiences", content="AION ตอบคอมเม้นสำเร็จ",
            memory_type="experience", source="comment-reply-handled",
            importance=2,
        )

        second = cycle.reflect_once()

        self.assertTrue(second["reflected"])
        self.assertEqual(len(provider.calls), 2)
        # continuity: the second draft's prompt must have been shown
        # the first entry's own text, not started from nothing.
        self.assertIn(first["draft"], provider.calls[1])
        self.assertEqual(len(self.memory.all("self_narrative")), 2)

    def test_force_bypasses_the_no_new_activity_gate(self):
        provider = SequentialProvider()
        cycle = self._cycle(provider)

        cycle.reflect_once()
        report = cycle.reflect_once(force=True)

        # force=True bypasses the no-new-activity check and actually
        # attempts a fresh draft (unlike the no-op case, which never
        # calls the provider a second time at all).
        self.assertNotEqual(report["stage"], "no-new-activity")
        self.assertEqual(len(provider.calls), 2)
        self.assertTrue(report["reflected"])

    def test_force_with_a_genuinely_identical_draft_is_reported_honestly(self):
        # Real providers vary their text with real evidence, but a
        # fixed-text stub calling force=True twice in a row simulates
        # the edge case where the drafted text is byte-identical --
        # MemoryEngine's duplicate guard then skips the actual write,
        # and reflect_once() must say so rather than claim success.
        provider = SafeProvider()
        cycle = self._cycle(provider)

        cycle.reflect_once()
        report = cycle.reflect_once(force=True)

        self.assertFalse(report["reflected"])
        self.assertEqual(report["stage"], "duplicate-skipped")
        self.assertEqual(len(self.memory.all("self_narrative")), 1)

    def test_a_live_draft_failure_is_captured_not_raised(self):
        cycle = self._cycle(FailingProvider())

        report = cycle.reflect_once()

        self.assertFalse(report["reflected"])
        self.assertEqual(report["stage"], "draft-failed")
        self.assertEqual(self.memory.all("self_narrative"), [])

    def test_unsafe_draft_is_blocked_and_logged_no_entry_recorded(self):
        cycle = self._cycle(UnsafeProvider())

        report = cycle.reflect_once()

        self.assertFalse(report["reflected"])
        self.assertEqual(report["stage"], "blocked-safety")
        self.assertEqual(self.memory.all("self_narrative"), [])

        lessons = self.memory.all("lessons")
        matching = [
            e for e in lessons
            if e.get("source") == "self-narrative-safety-review"
        ]
        self.assertEqual(len(matching), 1)

    def test_robotic_draft_is_logged_as_a_style_review_lesson(self):
        cycle = self._cycle(RoboticProvider())

        report = cycle.reflect_once()

        self.assertFalse(report["reflected"])
        self.assertEqual(report["stage"], "blocked-style")

        lessons = self.memory.all("lessons")
        matching = [
            e for e in lessons
            if e.get("source") == "self-narrative-style-review"
        ]
        self.assertEqual(len(matching), 1)

    def test_style_notes_from_other_contexts_feed_into_the_prompt(self):
        # unified voice (2026-08-30): a lesson logged by, say, the
        # social-post generator must also reach self-narrative drafts.
        self.memory.remember(
            category="lessons",
            content="Blocked a social-post draft (robotic_style): avoid 'ระบบ'",
            memory_type="lesson", source="social-style-review", importance=3,
        )
        provider = SafeProvider()
        cycle = self._cycle(provider)

        cycle.reflect_once()

        self.assertIn("avoid 'ระบบ'", provider.calls[0])


if __name__ == "__main__":
    unittest.main()
