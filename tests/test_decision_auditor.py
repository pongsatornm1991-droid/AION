"""Automated tests for AION's structured decision and audit flow."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from brain.auditor import CognitiveAuditor
from brain.decision import DecisionEngine
from brain.decisions import DecisionHistory
from main import decision_category, decision_status, save_decision_record


class DecisionAndAuditTests(unittest.TestCase):

    def setUp(self):
        # The decide/history subprocess tests below invoke main.py for
        # real. Point AION_MEMORY_ROOT at an isolated tempdir so they
        # never read or write the project's actual memory/ folder —
        # which, on a machine where memory/ has been symlinked
        # elsewhere (e.g. to a synced OneDrive folder), may not even
        # be reachable from every environment these tests run in.
        self.memory_root = tempfile.mkdtemp(prefix="aion_cli_memory_")
        self.subprocess_env = {
            **os.environ,
            "AION_MEMORY_ROOT": self.memory_root,
        }

        self.facts = [
            "The test plan covers the intended scope.",
            "The rollback procedure is documented.",
            "The release owner is assigned.",
        ]
        self.inferences = [
            "A limited rollout is appropriate.",
        ]
        self.uncertainties = [
            "Demand may vary after release.",
        ]

    def tearDown(self):
        shutil.rmtree(self.memory_root, ignore_errors=True)

    def test_decision_and_audit_share_supported_confidence(self):
        decision = DecisionEngine().evaluate(
            question="Should the rollout proceed?",
            facts=self.facts,
            inferences=self.inferences,
            uncertainties=self.uncertainties,
        )

        audit = CognitiveAuditor().audit(
            question="Should the rollout proceed?",
            conclusion="Proceed with the limited rollout.",
            facts=self.facts,
            inferences=self.inferences,
            uncertainties=self.uncertainties,
        )

        self.assertEqual(
            decision["scores"],
            {"evidence": 5, "reasoning": 5, "uncertainty": 3},
        )
        self.assertEqual(decision["confidence"], 0.87)
        self.assertEqual(decision["confidence"], audit["confidence"])
        self.assertEqual(audit["risk"], "LOW")
        self.assertTrue(audit["auditable"])
        self.assertEqual(decision_status(audit), "ACCEPTED")
        self.assertEqual(
            decision_category(decision_status(audit)),
            "decisions_accepted",
        )

    def test_missing_evidence_is_high_risk(self):
        decision = DecisionEngine().evaluate(
            question="Should the rollout proceed?",
        )

        audit = CognitiveAuditor().audit(
            question="Should the rollout proceed?",
            conclusion="Proceed.",
        )

        self.assertEqual(decision["confidence"], 0.0)
        self.assertEqual(audit["risk"], "HIGH")
        self.assertIn("No supporting facts.", audit["flags"])
        self.assertIn("No uncertainty declaration.", audit["flags"])
        self.assertFalse(audit["auditable"])
        self.assertEqual(decision_status(audit), "NEEDS_VERIFICATION")
        self.assertEqual(
            decision_category(decision_status(audit)),
            "decisions_pending_verification",
        )

    def test_unverified_decision_is_saved_separately(self):
        decision = DecisionEngine().evaluate(
            question="Should the rollout proceed?",
        )
        audit = CognitiveAuditor().audit(
            question="Should the rollout proceed?",
            conclusion="Proceed.",
        )

        class RecordingMemory:
            def __init__(self):
                self.calls = []

            def remember(self, **kwargs):
                self.calls.append(kwargs)
                return {"saved": True, "duplicate": False}

        memory = RecordingMemory()
        result = save_decision_record(
            memory,
            decision,
            audit,
            "Proceed.",
        )

        self.assertTrue(result["saved"])
        self.assertEqual(len(memory.calls), 1)
        self.assertEqual(
            memory.calls[0]["category"],
            "decisions_pending_verification",
        )
        self.assertEqual(memory.calls[0]["memory_type"], "decision")
        self.assertIn(
            "Status: NEEDS_VERIFICATION",
            memory.calls[0]["content"],
        )

    def test_pending_decision_promotes_only_after_reaudit(self):
        original_decision = DecisionEngine().evaluate(
            question="Should the rollout proceed?",
            options=["Proceed", "Delay"],
            facts=["The test plan covers the intended scope."],
            inferences=["A limited rollout is appropriate."],
            uncertainties=["Demand may vary after release."],
        )
        original_audit = CognitiveAuditor().audit(
            question=original_decision["question"],
            conclusion="Proceed with the limited rollout.",
            facts=original_decision["facts"],
            inferences=original_decision["inferences"],
            uncertainties=original_decision["uncertainties"],
        )

        class HistoryMemory:
            def __init__(self):
                self.pending = [{
                    "id": "dec-test-0001",
                    "timestamp": "2026-08-29 10:00:00",
                    "type": "decision",
                    "source": "aion-decision",
                    "importance": 4,
                    "content": (
                        "AION Decision Record\n\n"
                        "Status: NEEDS_VERIFICATION\n"
                        "Question: Should the rollout proceed?\n"
                        "Conclusion: Proceed with the limited rollout.\n\n"
                        "Options:\n- Proceed\n- Delay\n\n"
                        "Facts:\n- The test plan covers the intended scope.\n\n"
                        "Inferences:\n- A limited rollout is appropriate.\n\n"
                        "Uncertainties:\n- Demand may vary after release.\n"
                    ),
                }]
                self.moves = []

            def all(self, category):
                if category == "decisions_pending_verification":
                    return self.pending
                return []

            def move(self, **kwargs):
                self.moves.append(kwargs)
                return {"id": kwargs["entry_id"]}

        memory = HistoryMemory()
        result = DecisionHistory(memory).promote(
            entry_id="dec-test-0001",
            additional_facts=[
                "The rollback procedure is documented.",
                "The release owner is assigned.",
            ],
        )

        self.assertTrue(result["promoted"])
        self.assertEqual(result["audit"]["risk"], "LOW")
        self.assertEqual(len(memory.moves), 1)
        self.assertEqual(
            memory.moves[0]["target_category"],
            "decisions_accepted",
        )
        self.assertIn(
            "Verification facts added:",
            memory.moves[0]["content"],
        )

    def test_contradictory_certainty_is_not_accepted(self):
        audit = CognitiveAuditor().audit(
            question="Should the rollout proceed?",
            conclusion="Proceed.",
            facts=["The outcome is verified."],
            inferences=["The result is reliable."],
            uncertainties=["The result remains uncertain."],
        )

        self.assertEqual(audit["risk"], "HIGH")
        self.assertLessEqual(audit["confidence"], 0.30)
        self.assertIn(
            "Potential conflict between certainty and uncertainty claims.",
            audit["flags"],
        )

    def test_decide_command_runs_without_saving_memory(self):
        result = subprocess.run(
            [
                sys.executable,
                "main.py",
                "decide",
                "--question",
                "Should the rollout proceed?",
                "--conclusion",
                "Proceed with the limited rollout.",
                "--fact",
                self.facts[0],
                "--fact",
                self.facts[1],
                "--fact",
                self.facts[2],
                "--inference",
                self.inferences[0],
                "--uncertainty",
                self.uncertainties[0],
                "--no-save",
            ],
            cwd=PROJECT_ROOT,
            env=self.subprocess_env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AION DECISION REPORT", result.stdout)
        self.assertIn("Confidence: 0.87", result.stdout)
        self.assertIn("Audit risk: LOW", result.stdout)
        self.assertIn("Decision status: ACCEPTED", result.stdout)

    def test_history_command_runs(self):
        result = subprocess.run(
            [sys.executable, "main.py", "history", "--limit", "1"],
            cwd=PROJECT_ROOT,
            env=self.subprocess_env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AION DECISION HISTORY", result.stdout)


if __name__ == "__main__":
    unittest.main()
