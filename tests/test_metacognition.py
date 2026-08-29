"""Offline, filesystem-level tests for MetacognitionEngine.

Every number MetacognitionEngine reports is computed directly from
memory already on disk (experiment outcomes, lessons, MemoryEngine's
own quality/stat primitives) -- no AI provider is involved anywhere,
so this suite needs no stub/mock provider and runs fully
deterministically.
"""

import shutil
import tempfile
import unittest

from brain.curiosity import CuriosityEngine
from brain.experiments import ExperimentEngine
from brain.memory import MemoryEngine
from brain.metacognition import MetacognitionEngine


class CalibrationReportTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_metacog_calib_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.experiments = ExperimentEngine(self.memory)
        self.meta = MetacognitionEngine(self.memory, experiments=self.experiments)
        self._prediction_counter = 0

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_rejects_invalid_bucket_size(self):
        with self.assertRaises(ValueError):
            self.meta.calibration_report(bucket_size=0)

        with self.assertRaises(ValueError):
            self.meta.calibration_report(bucket_size=1.5)

    def test_empty_when_no_experiments_observed(self):
        report = self.meta.calibration_report()

        self.assertEqual(report["sample_size"], 0)
        self.assertEqual(report["buckets"], [])
        self.assertIsNone(report["overall_calibration_error"])

    def test_predicted_only_experiments_are_excluded(self):
        self.experiments.predict("Never observed.", confidence=0.8)

        report = self.meta.calibration_report()
        self.assertEqual(report["sample_size"], 0)

    def _observe(self, confidence, matched, error=None):
        # Each prediction's content must be unique -- MemoryEngine
        # silently drops exact-duplicate content (category + content +
        # type + source), and every call in these tests would
        # otherwise share the same "Prediction." text at a given
        # confidence.
        self._prediction_counter += 1
        saved = self.experiments.predict(
            f"Prediction {self._prediction_counter}.", confidence=confidence
        )
        return self.experiments.observe(
            saved["id"], "Result.", matched=matched, evidence=["note"],
            error_description=error,
        )

    def test_bucket_below_min_samples_is_flagged_insufficient(self):
        self._observe(0.9, True)
        self._observe(0.9, True)

        report = self.meta.calibration_report(min_samples_per_bucket=3)
        bucket = next(b for b in report["buckets"] if b["range"] == (0.8, 1.0))

        self.assertEqual(bucket["count"], 2)
        self.assertFalse(bucket["sufficient_data"])
        self.assertEqual(bucket["assessment"], "insufficient_data")
        self.assertIsNone(bucket["calibration_gap"])
        # Not enough data anywhere -> no overall calibration error either.
        self.assertIsNone(report["overall_calibration_error"])

    def test_overconfident_bucket_detected(self):
        for _ in range(3):
            self._observe(0.9, False, error="Did not happen.")

        report = self.meta.calibration_report(min_samples_per_bucket=3)
        bucket = next(b for b in report["buckets"] if b["range"] == (0.8, 1.0))

        self.assertTrue(bucket["sufficient_data"])
        self.assertEqual(bucket["match_rate"], 0.0)
        self.assertEqual(bucket["assessment"], "overconfident")
        self.assertAlmostEqual(bucket["calibration_gap"], 0.9, places=3)
        self.assertAlmostEqual(report["overall_calibration_error"], 0.9, places=3)

    def test_well_calibrated_bucket_detected(self):
        # Confidence ~0.5, matches about half the time.
        self._observe(0.5, True)
        self._observe(0.5, False, error="Missed.")
        self._observe(0.5, True)
        self._observe(0.5, False, error="Missed.")

        report = self.meta.calibration_report(min_samples_per_bucket=3)
        bucket = next(b for b in report["buckets"] if b["range"] == (0.4, 0.6))

        self.assertTrue(bucket["sufficient_data"])
        self.assertEqual(bucket["match_rate"], 0.5)
        self.assertEqual(bucket["assessment"], "well-calibrated")

    def test_underconfident_bucket_detected(self):
        # Confidence 0.2, but matches every time -> underconfident.
        for _ in range(3):
            self._observe(0.2, True)

        report = self.meta.calibration_report(min_samples_per_bucket=3)
        bucket = next(b for b in report["buckets"] if b["range"] == (0.2, 0.4))

        self.assertEqual(bucket["match_rate"], 1.0)
        self.assertEqual(bucket["assessment"], "underconfident")
        self.assertLess(bucket["calibration_gap"], 0)

    def test_abandoned_after_observation_still_counts_toward_calibration(self):
        observed = self._observe(0.9, True)
        self.experiments.abandon(observed["id"], reason="Data was invalid.")

        report = self.meta.calibration_report(min_samples_per_bucket=1)
        self.assertEqual(report["sample_size"], 1)


class RecurringErrorReportTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_metacog_errors_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.experiments = ExperimentEngine(self.memory)
        self.curiosity = CuriosityEngine(self.memory)
        self.meta = MetacognitionEngine(self.memory, experiments=self.experiments)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_when_no_lessons(self):
        report = self.meta.recurring_error_report()

        self.assertEqual(report["total_lessons"], 0)
        self.assertEqual(report["sources"], [])
        self.assertEqual(report["recurring"], [])

    def test_groups_by_source_and_flags_recurring(self):
        for i in range(3):
            q = self.curiosity.raise_question(f"Q{i}", completion_criteria="c")
            self.curiosity.abandon_question(q["id"], reason="Not relevant.")

        p = self.experiments.predict("P", confidence=0.5)
        self.experiments.abandon(p["id"], reason="No longer relevant.")

        report = self.meta.recurring_error_report(min_occurrences=2)

        self.assertEqual(report["total_lessons"], 4)
        sources = {item["source"]: item["count"] for item in report["sources"]}
        self.assertEqual(sources["question-abandonment"], 3)
        self.assertEqual(sources["experiment-abandonment"], 1)

        recurring_sources = [item["source"] for item in report["recurring"]]
        self.assertIn("question-abandonment", recurring_sources)
        self.assertNotIn("experiment-abandonment", recurring_sources)

    def test_min_occurrences_threshold_is_respected(self):
        q = self.curiosity.raise_question("Q", completion_criteria="c")
        self.curiosity.abandon_question(q["id"], reason="Not relevant.")

        report = self.meta.recurring_error_report(min_occurrences=2)
        self.assertEqual(report["recurring"], [])

        report_lenient = self.meta.recurring_error_report(min_occurrences=1)
        self.assertEqual(len(report_lenient["recurring"]), 1)

    def test_limit_truncates_sources(self):
        for name in ["a", "b", "c"]:
            q = self.curiosity.raise_question(name, completion_criteria="c")
            self.curiosity.abandon_question(q["id"], reason=f"reason-{name}")

        # All abandonments share the same source label, so this just
        # confirms the limit parameter is honored at all.
        report = self.meta.recurring_error_report(limit=1)
        self.assertLessEqual(len(report["sources"]), 1)


class MemoryQualityOverviewTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_metacog_quality_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.experiments = ExperimentEngine(self.memory)
        self.meta = MetacognitionEngine(self.memory, experiments=self.experiments)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_when_no_categories_on_disk(self):
        report = self.meta.memory_quality_overview()

        self.assertEqual(report["categories"], {})
        self.assertEqual(report["total_entries"], 0)
        self.assertEqual(report["overall_average_quality"], 0.0)
        self.assertEqual(report["flagged_low_quality"], [])

    def test_auto_discovers_categories_from_disk(self):
        self.experiments.predict("A short prediction.", confidence=0.5)

        report = self.meta.memory_quality_overview()
        self.assertIn("experiments", report["categories"])
        self.assertEqual(report["categories"]["experiments"]["total"], 1)
        self.assertEqual(report["total_entries"], 1)

    def test_explicit_categories_overrides_auto_discovery(self):
        self.experiments.predict("A short prediction.", confidence=0.5)

        report = self.meta.memory_quality_overview(categories=["experiments"])
        self.assertEqual(set(report["categories"].keys()), {"experiments"})

        empty_report = self.meta.memory_quality_overview(categories=["does_not_exist"])
        self.assertEqual(empty_report["categories"]["does_not_exist"]["total"], 0)

    def test_thin_category_is_never_flagged_low_quality(self):
        # A single very short, low-quality entry -- but below the
        # 3-entry minimum, so it must not be flagged.
        self.memory.remember(
            category="experiences", content="x", memory_type="experience",
            importance=1,
        )

        report = self.meta.memory_quality_overview()
        self.assertEqual(report["flagged_low_quality"], [])

    def test_category_with_enough_low_quality_entries_is_flagged(self):
        # Content must be unique per entry -- identical content is
        # silently deduplicated by MemoryEngine.
        for i in range(3):
            self.memory.remember(
                category="experiences", content=f"x{i}", memory_type="experience",
                importance=1,
            )

        report = self.meta.memory_quality_overview(low_quality_threshold=2.5)
        self.assertEqual(report["categories"]["experiences"]["total"], 3)
        self.assertIn("experiences", report["flagged_low_quality"])

    def test_overall_average_is_weighted_by_entry_count(self):
        # 1 high-quality entry (long, structured, high importance) and
        # 3 low-quality entries -- the weighted average should be
        # pulled toward the more numerous low-quality group.
        self.memory.remember(
            category="beliefs",
            content=(
                "FACT: Something well-documented and long enough to "
                "score highly on every quality dimension checked."
            ),
            memory_type="belief",
            importance=5,
        )

        for i in range(3):
            self.memory.remember(
                category="experiences", content=f"x{i}", memory_type="experience",
                importance=1,
            )

        report = self.meta.memory_quality_overview()
        beliefs_avg = report["categories"]["beliefs"]["average_quality"]
        experiences_avg = report["categories"]["experiences"]["average_quality"]

        self.assertGreater(beliefs_avg, experiences_avg)
        self.assertLess(report["overall_average_quality"], beliefs_avg)
        self.assertGreater(report["overall_average_quality"], experiences_avg)


class FullReportTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_metacog_full_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.meta = MetacognitionEngine(self.memory)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_full_report_combines_all_sections(self):
        report = self.meta.full_report()

        self.assertIn("calibration", report)
        self.assertIn("recurring_errors", report)
        self.assertIn("memory_quality", report)
        self.assertIn("tool_reliability", report)

    def test_tool_reliability_is_never_fabricated(self):
        report = self.meta.full_report()

        self.assertEqual(report["tool_reliability"]["status"], "not_applicable")
        self.assertIn("reason", report["tool_reliability"])


if __name__ == "__main__":
    unittest.main()
