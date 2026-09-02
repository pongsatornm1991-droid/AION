"""Offline, filesystem-level tests for BeliefSystem.

No AI provider is involved anywhere in BeliefSystem itself — forming,
revising, retracting, and querying beliefs is pure code, so this suite
needs no stub/mock provider and runs fully deterministically.
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from brain.beliefs import BeliefSystem
from brain.memory import MemoryEngine


class BeliefSystemTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_beliefs_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)
        self.beliefs = BeliefSystem(self.memory)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -----------------------------------------------------
    # FORM
    # -----------------------------------------------------

    def test_form_belief_requires_evidence(self):
        with self.assertRaises(ValueError):
            self.beliefs.form_belief(
                "Something is true.", confidence=0.8, evidence=[]
            )

    def test_form_belief_requires_evidence_not_none(self):
        with self.assertRaises(ValueError):
            self.beliefs.form_belief(
                "Something is true.", confidence=0.8, evidence=None
            )

    def test_form_belief_rejects_out_of_range_confidence(self):
        with self.assertRaises(ValueError):
            self.beliefs.form_belief(
                "Something is true.",
                confidence=1.5,
                evidence=["a note"],
            )

    def test_form_belief_rejects_empty_statement(self):
        with self.assertRaises(ValueError):
            self.beliefs.form_belief(
                "   ", confidence=0.5, evidence=["a note"]
            )

    def test_form_belief_saves_and_survives_disk_roundtrip(self):
        saved = self.beliefs.form_belief(
            "Staged rollouts reduce rollback risk.",
            confidence=0.7,
            evidence=[{"id": "dec123", "description": "Accepted LOW risk."}],
            tags=["rollout"],
        )

        self.assertEqual(saved["related"], ["dec123"])
        self.assertEqual(saved["tags"], ["rollout"])
        self.assertEqual(saved["importance"], 4)  # 1 + round(0.7*4) = 4

        active = self.beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertEqual(
            active[0]["statement"],
            "Staged rollouts reduce rollback risk.",
        )
        self.assertEqual(active[0]["confidence"], 0.7)
        # 2026-09-02: beliefs no longer expire by default (see
        # BeliefSystem.DEFAULT_EXPIRES_DAYS) -- a belief formed
        # without an explicit expires_in_days stays active
        # indefinitely, not just until some default lapses.
        self.assertIsNone(active[0]["expires"])
        self.assertIsNone(active[0]["predecessor"])

    def test_form_belief_never_expires_by_default(self):
        """At the user's explicit request (2026-09-02): a belief
        formed with no explicit expires_in_days must stay active
        forever, not silently age out after some default window."""
        self.beliefs.form_belief(
            "AION should keep captions in Thai.",
            confidence=0.6,
            evidence=[{"description": "User confirmed this choice."}],
        )

        active = self.beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertIsNone(active[0]["expires"])

    def test_active_beliefs_filters_by_topic(self):
        self.beliefs.form_belief(
            "About rollouts.", 0.6, evidence=["note"], tags=["rollout"]
        )
        self.beliefs.form_belief(
            "About something else.", 0.6, evidence=["note"], tags=["other"]
        )

        rollout_only = self.beliefs.active_beliefs(topic="rollout")
        self.assertEqual(len(rollout_only), 1)
        self.assertEqual(rollout_only[0]["statement"], "About rollouts.")

    # -----------------------------------------------------
    # REVISE
    # -----------------------------------------------------

    def test_revise_belief_supersedes_old_and_creates_new(self):
        original = self.beliefs.form_belief(
            "Initial claim.", 0.5, evidence=["note"]
        )

        revised = self.beliefs.revise_belief(
            original["id"],
            reason="New evidence changed my mind.",
            new_confidence=0.9,
            new_statement="Revised claim.",
        )

        self.assertNotEqual(revised["id"], original["id"])
        self.assertIn(original["id"], revised["related"])

        active = self.beliefs.active_beliefs()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["id"], revised["id"])
        self.assertEqual(active[0]["confidence"], 0.9)
        self.assertEqual(active[0]["statement"], "Revised claim.")
        self.assertEqual(active[0]["predecessor"], original["id"])

    def test_revise_belief_rejects_missing_reason(self):
        original = self.beliefs.form_belief(
            "Initial claim.", 0.5, evidence=["note"]
        )

        with self.assertRaises(ValueError):
            self.beliefs.revise_belief(original["id"], reason="   ")

    def test_cannot_revise_an_already_superseded_belief(self):
        original = self.beliefs.form_belief(
            "Initial claim.", 0.5, evidence=["note"]
        )
        self.beliefs.revise_belief(original["id"], reason="First revision.")

        with self.assertRaises(ValueError):
            self.beliefs.revise_belief(
                original["id"], reason="Second revision attempt."
            )

    def test_history_walks_full_lineage_oldest_first(self):
        first = self.beliefs.form_belief(
            "v1.", 0.4, evidence=["note"]
        )
        second = self.beliefs.revise_belief(
            first["id"], reason="revision 1", new_confidence=0.6
        )
        third = self.beliefs.revise_belief(
            second["id"], reason="revision 2", new_confidence=0.8
        )

        history = self.beliefs.history(third["id"])

        self.assertEqual(
            [entry["id"] for entry in history],
            [first["id"], second["id"], third["id"]],
        )

    def test_history_of_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.beliefs.history("does-not-exist")

    # -----------------------------------------------------
    # RETRACT
    # -----------------------------------------------------

    def test_retract_belief_removes_it_from_active_and_logs_a_lesson(self):
        saved = self.beliefs.form_belief(
            "Claim to retract.", 0.5, evidence=["note"]
        )

        self.beliefs.retract_belief(saved["id"], reason="Turned out false.")

        self.assertEqual(self.beliefs.active_beliefs(), [])

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("Retracted belief", lessons[0]["content"])
        self.assertIn(saved["id"], lessons[0]["related"])

    def test_cannot_retract_an_already_retracted_belief(self):
        saved = self.beliefs.form_belief(
            "Claim to retract.", 0.5, evidence=["note"]
        )
        self.beliefs.retract_belief(saved["id"], reason="First retraction.")

        with self.assertRaises(ValueError):
            self.beliefs.retract_belief(
                saved["id"], reason="Second retraction attempt."
            )

    # -----------------------------------------------------
    # EXPIRATION
    # -----------------------------------------------------

    def test_expired_belief_is_excluded_from_active_beliefs(self):
        saved = self.beliefs.form_belief(
            "Short-lived claim.",
            0.5,
            evidence=["note"],
            expires_in_days=1,
        )

        with mock.patch("brain.beliefs.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now() + timedelta(days=3)
            mock_dt.strptime = datetime.strptime

            self.assertEqual(self.beliefs.active_beliefs(), [])
            self.assertEqual(
                self.beliefs.status_of(self.memory.all("beliefs")[0]),
                "expired",
            )

        # Outside the patched window, the belief is active again — this
        # documents that expiration is computed at read time, not a
        # stored, one-way transition.
        self.assertEqual(len(self.beliefs.active_beliefs()), 1)

    def test_expires_in_days_zero_means_never_expires(self):
        self.beliefs.form_belief(
            "Permanent claim.",
            0.5,
            evidence=["note"],
            expires_in_days=0,
        )

        entry = self.memory.all("beliefs")[0]
        self.assertEqual(self.beliefs.status_of(entry), "active")

        with mock.patch("brain.beliefs.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now() + timedelta(days=3650)
            mock_dt.strptime = datetime.strptime

            self.assertEqual(self.beliefs.status_of(entry), "active")

    def test_rejects_negative_expires_in_days(self):
        with self.assertRaises(ValueError):
            self.beliefs.form_belief(
                "Claim.", 0.5, evidence=["note"], expires_in_days=-1
            )


if __name__ == "__main__":
    unittest.main()
