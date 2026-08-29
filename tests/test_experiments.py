"""Offline, filesystem-level tests for ExperimentEngine.

No AI provider is involved anywhere in ExperimentEngine — predicting,
observing, concluding, and abandoning experiments is pure code, so
this suite needs no stub/mock provider and runs fully
deterministically. The optional BeliefSystem integration at conclude()
is exercised with a real (tempdir-backed) BeliefSystem instance, since
that integration is itself pure code with no AI call either.
"""

import shutil
import tempfile
import unittest

from brain.beliefs import BeliefSystem
from brain.experiments import ExperimentEngine
from brain.memory import MemoryEngine


class ExperimentEngineTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_experiments_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.experiments = ExperimentEngine(self.memory)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -----------------------------------------------------
    # PREDICT
    # -----------------------------------------------------

    def test_predict_rejects_empty_prediction(self):
        with self.assertRaises(ValueError):
            self.experiments.predict("   ", confidence=0.5)

    def test_predict_rejects_out_of_range_confidence(self):
        with self.assertRaises(ValueError):
            self.experiments.predict("Something happens.", confidence=1.5)

    def test_predict_rejects_bool_confidence(self):
        with self.assertRaises(TypeError):
            self.experiments.predict("Something happens.", confidence=True)

    def test_predict_rejects_non_numeric_confidence(self):
        with self.assertRaises(TypeError):
            self.experiments.predict("Something happens.", confidence="high")

    def test_predict_requires_no_evidence(self):
        # A prediction is a stated expectation, not a claim of fact —
        # unlike form_belief()/answer_question()/resolve_item(), no
        # evidence argument exists at all for predict().
        saved = self.experiments.predict("Something happens.", confidence=0.5)
        self.assertIsNotNone(saved["id"])

    def test_predict_saves_and_survives_disk_roundtrip(self):
        saved = self.experiments.predict(
            "Staged rollout reduces rollback incidents.",
            confidence=0.7,
            tags=["rollout"],
        )

        self.assertEqual(saved["tags"], ["rollout"])
        self.assertEqual(saved["importance"], 4)  # 1 + round(0.7*4) = 4

        pending = self.experiments.pending_experiments()
        self.assertEqual(len(pending), 1)
        self.assertEqual(
            pending[0]["prediction"],
            "Staged rollout reduces rollback incidents.",
        )
        self.assertEqual(pending[0]["confidence"], 0.7)
        self.assertIsNone(pending[0]["predecessor"])
        self.assertEqual(self.experiments.status_of(pending[0]), "predicted")

    # -----------------------------------------------------
    # OBSERVE
    # -----------------------------------------------------

    def test_observe_requires_evidence(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(ValueError):
            self.experiments.observe(
                saved["id"], "X happened.", matched=True, evidence=[]
            )

    def test_observe_rejects_empty_result(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(ValueError):
            self.experiments.observe(
                saved["id"], "   ", matched=True, evidence=["note"]
            )

    def test_observe_requires_matched_to_be_bool(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(TypeError):
            self.experiments.observe(
                saved["id"], "X happened.", matched="yes", evidence=["note"]
            )

    def test_observe_mismatch_requires_error_description(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(ValueError):
            self.experiments.observe(
                saved["id"], "X did not happen.", matched=False,
                evidence=["note"],
            )

    def test_observe_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.experiments.observe(
                "does-not-exist", "X happened.", matched=True,
                evidence=["note"],
            )

    def test_cannot_observe_an_already_observed_experiment(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )

        with self.assertRaises(ValueError):
            self.experiments.observe(
                observed["id"], "Again.", matched=True, evidence=["note"]
            )

    def test_observe_supersedes_prediction_and_links_evidence(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        observed = self.experiments.observe(
            saved["id"],
            "X happened as predicted.",
            matched=True,
            evidence=[{"id": "dec42", "description": "Confirmed."}],
        )

        self.assertNotEqual(observed["id"], saved["id"])
        self.assertIn("dec42", observed["related"])
        self.assertIn(saved["id"], observed["related"])
        self.assertEqual(self.experiments.status_of(observed), "observed")
        self.assertEqual(self.experiments.pending_experiments(), [])

        awaiting = self.experiments.awaiting_conclusion()
        self.assertEqual(len(awaiting), 1)
        self.assertEqual(awaiting[0]["id"], observed["id"])
        self.assertTrue(awaiting[0]["matched"])

    def test_observe_mismatch_with_error_description_succeeds(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        observed = self.experiments.observe(
            saved["id"],
            "X did not happen.",
            matched=False,
            evidence=["note"],
            error_description="Confounding factor Y was present.",
        )

        self.assertFalse(observed["related"] == [])
        parsed_status = self.experiments.status_of(observed)
        self.assertEqual(parsed_status, "observed")

        awaiting = self.experiments.awaiting_conclusion()
        self.assertFalse(awaiting[0]["matched"])

    # -----------------------------------------------------
    # CONCLUDE
    # -----------------------------------------------------

    def test_cannot_conclude_before_observed(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(ValueError):
            self.experiments.conclude(saved["id"], "Some lesson.")

    def test_conclude_rejects_empty_lesson(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )

        with self.assertRaises(ValueError):
            self.experiments.conclude(observed["id"], "   ")

    def test_cannot_conclude_an_already_concluded_experiment(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )
        result = self.experiments.conclude(observed["id"], "Lesson.")
        concluded = result["experiment"]

        with self.assertRaises(ValueError):
            self.experiments.conclude(concluded["id"], "Another lesson.")

    def test_conclude_supersedes_and_logs_a_companion_lesson(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )

        result = self.experiments.conclude(
            observed["id"], "X reliably happens under these conditions."
        )
        concluded = result["experiment"]

        self.assertIsNone(result["revised_belief"])
        self.assertNotEqual(concluded["id"], observed["id"])
        self.assertEqual(self.experiments.status_of(concluded), "concluded")
        self.assertEqual(self.experiments.awaiting_conclusion(), [])

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("experiment", lessons[0]["content"].lower())
        self.assertIn(
            "X reliably happens under these conditions.",
            lessons[0]["content"],
        )
        self.assertIn(concluded["id"], lessons[0]["related"])

    def test_conclude_can_revise_an_existing_belief(self):
        beliefs = BeliefSystem(self.memory)
        belief = beliefs.form_belief(
            "Staged rollouts are safer.",
            confidence=0.6,
            evidence=[{"id": "dec1", "description": "Past incident."}],
        )

        saved = self.experiments.predict(
            "Staged rollout reduces rollback incidents.", confidence=0.7
        )
        observed = self.experiments.observe(
            saved["id"],
            "Rollbacks dropped 40% over two weeks.",
            matched=True,
            evidence=[{"id": "dec42", "description": "Rollback log."}],
        )

        result = self.experiments.conclude(
            observed["id"],
            "Confirmed staged rollout reduces incidents; raise confidence.",
            belief_system=beliefs,
            belief_id=belief["id"],
            new_belief_confidence=0.85,
        )

        revised = result["revised_belief"]
        self.assertIsNotNone(revised)
        self.assertNotEqual(revised["id"], belief["id"])

        active = beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["id"], revised["id"])
        self.assertEqual(active[0]["confidence"], 0.85)

    def test_conclude_without_belief_id_never_touches_beliefs(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )

        result = self.experiments.conclude(observed["id"], "Lesson.")

        self.assertIsNone(result["revised_belief"])
        self.assertEqual(self.memory.all("beliefs"), [])

    # -----------------------------------------------------
    # ABANDON
    # -----------------------------------------------------

    def test_abandon_requires_reason(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)

        with self.assertRaises(ValueError):
            self.experiments.abandon(saved["id"], reason="   ")

    def test_abandon_from_predicted_tags_and_logs_a_lesson(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        self.experiments.abandon(saved["id"], reason="No longer relevant.")

        entry = self.experiments._get(saved["id"])
        self.assertEqual(self.experiments.status_of(entry), "abandoned")
        self.assertEqual(self.experiments.pending_experiments(), [])

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("Abandoned experiment", lessons[0]["content"])
        self.assertIn(saved["id"], lessons[0]["related"])

    def test_abandon_from_observed_also_allowed(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )
        self.experiments.abandon(observed["id"], reason="Data was invalid.")

        entry = self.experiments._get(observed["id"])
        self.assertEqual(self.experiments.status_of(entry), "abandoned")

    def test_cannot_abandon_a_concluded_experiment(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )
        result = self.experiments.conclude(observed["id"], "Lesson.")

        with self.assertRaises(ValueError):
            self.experiments.abandon(
                result["experiment"]["id"], reason="Too late."
            )

    def test_cannot_observe_or_conclude_an_abandoned_experiment(self):
        saved = self.experiments.predict("X happens.", confidence=0.5)
        self.experiments.abandon(saved["id"], reason="No longer relevant.")

        with self.assertRaises(ValueError):
            self.experiments.observe(
                saved["id"], "X happened.", matched=True, evidence=["note"]
            )

        with self.assertRaises(ValueError):
            self.experiments.conclude(saved["id"], "Lesson.")

    # -----------------------------------------------------
    # HISTORY / QUERIES
    # -----------------------------------------------------

    def test_history_walks_full_predict_observe_conclude_chain(self):
        predicted = self.experiments.predict("X happens.", confidence=0.5)
        observed = self.experiments.observe(
            predicted["id"], "X happened.", matched=True, evidence=["note"]
        )
        result = self.experiments.conclude(observed["id"], "Lesson.")
        concluded = result["experiment"]

        history = self.experiments.history(concluded["id"])

        self.assertEqual(
            [entry["id"] for entry in history],
            [predicted["id"], observed["id"], concluded["id"]],
        )

    def test_history_of_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.experiments.history("does-not-exist")

    def test_pending_and_awaiting_are_mutually_exclusive_and_sorted(self):
        first = self.experiments.predict("First.", confidence=0.4)
        second = self.experiments.predict("Second.", confidence=0.6)
        self.experiments.observe(
            second["id"], "Observed.", matched=True, evidence=["note"]
        )

        pending = self.experiments.pending_experiments()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], first["id"])

        awaiting = self.experiments.awaiting_conclusion()
        self.assertEqual(len(awaiting), 1)
        self.assertEqual(awaiting[0]["prediction"], "Second.")

    def test_pending_experiments_respects_limit(self):
        for i in range(3):
            self.experiments.predict(f"Prediction {i}.", confidence=0.5)

        limited = self.experiments.pending_experiments(limit=2)
        self.assertEqual(len(limited), 2)


    # -----------------------------------------------------
    # OBSERVED_EXPERIMENTS (feeds Metacognition's calibration report)
    # -----------------------------------------------------

    def test_observed_experiments_excludes_predicted_only(self):
        self.experiments.predict("Never observed.", confidence=0.5)

        self.assertEqual(self.experiments.observed_experiments(), [])

    def test_observed_experiments_includes_observed_and_concluded(self):
        saved = self.experiments.predict("X happens.", confidence=0.7)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=True, evidence=["note"]
        )

        only_observed = self.experiments.observed_experiments()
        self.assertEqual(len(only_observed), 1)
        self.assertEqual(only_observed[0]["id"], observed["id"])
        self.assertTrue(only_observed[0]["matched"])
        self.assertEqual(only_observed[0]["confidence"], 0.7)

        result = self.experiments.conclude(observed["id"], "Lesson.")
        concluded = result["experiment"]

        after_conclude = self.experiments.observed_experiments()
        self.assertEqual(len(after_conclude), 1)
        self.assertEqual(after_conclude[0]["id"], concluded["id"])
        self.assertTrue(after_conclude[0]["matched"])

    def test_observed_experiments_includes_abandoned_after_observation(self):
        saved = self.experiments.predict("X happens.", confidence=0.6)
        observed = self.experiments.observe(
            saved["id"], "X happened.", matched=False, evidence=["note"],
            error_description="Confound present.",
        )
        self.experiments.abandon(observed["id"], reason="Data was invalid.")

        results = self.experiments.observed_experiments()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], observed["id"])
        self.assertFalse(results[0]["matched"])

    def test_observed_experiments_excludes_abandoned_before_observation(self):
        saved = self.experiments.predict("X happens.", confidence=0.6)
        self.experiments.abandon(saved["id"], reason="No longer relevant.")

        self.assertEqual(self.experiments.observed_experiments(), [])

    def test_observed_experiments_respects_limit(self):
        for i in range(3):
            saved = self.experiments.predict(f"P{i}", confidence=0.5)
            self.experiments.observe(
                saved["id"], f"Result {i}", matched=True, evidence=["note"]
            )

        limited = self.experiments.observed_experiments(limit=2)
        self.assertEqual(len(limited), 2)


if __name__ == "__main__":
    unittest.main()
