"""Offline, filesystem-level tests for ToolRegistry and ToolLifecycle.

No AI provider is involved anywhere -- registering stub tools,
proposing/approving/executing/recovering/abandoning actions, and the
kill switch are all pure code, so this suite needs no stub/mock AI
provider (only a couple of tests mock the clock, exactly like
test_beliefs.py's expiration test) and runs fully deterministically.
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from brain.memory import MemoryEngine
from brain.tools import (
    ActionLevel,
    ToolLifecycle,
    ToolRegistry,
    build_builtin_tools,
)


def _boom():
    raise RuntimeError("kaboom")


class ToolRegistryTests(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()

    def test_register_and_get(self):
        self.registry.register("noop", lambda: None, ActionLevel.READ_ONLY, "desc")

        spec = self.registry.get("noop")
        self.assertEqual(spec["level"], ActionLevel.READ_ONLY)
        self.assertEqual(spec["description"], "desc")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.registry.get("does-not-exist"))

    def test_register_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            self.registry.register("   ", lambda: None, ActionLevel.READ_ONLY)

    def test_register_rejects_reserved_kill_switch_name(self):
        with self.assertRaises(ValueError):
            self.registry.register(
                "__kill_switch__", lambda: None, ActionLevel.READ_ONLY
            )

    def test_register_rejects_duplicate_name(self):
        self.registry.register("noop", lambda: None, ActionLevel.READ_ONLY)

        with self.assertRaises(ValueError):
            self.registry.register("noop", lambda: None, ActionLevel.LOW_RISK)

    def test_register_rejects_unknown_level(self):
        with self.assertRaises(ValueError):
            self.registry.register("noop", lambda: None, "EXTREME_RISK")

    def test_register_rejects_non_callable(self):
        with self.assertRaises(TypeError):
            self.registry.register("noop", "not-a-function", ActionLevel.READ_ONLY)

    def test_list_tools(self):
        self.registry.register("a", lambda: None, ActionLevel.READ_ONLY, "d1")
        self.registry.register("b", lambda: None, ActionLevel.HIGH_RISK, "d2")

        names = {tool["name"] for tool in self.registry.list_tools()}
        self.assertEqual(names, {"a", "b"})


class ToolLifecycleTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_tools_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)

        self.registry = ToolRegistry()
        self.registry.register(
            "noop_read", lambda: "ok", ActionLevel.READ_ONLY, "read-only"
        )
        self.registry.register(
            "noop_low", lambda x=1: x * 2, ActionLevel.LOW_RISK, "low-risk"
        )
        self.registry.register("boom", _boom, ActionLevel.HIGH_RISK, "always fails")

        self.lc = ToolLifecycle(
            self.memory,
            registry=self.registry,
            budgets={ActionLevel.LOW_RISK: 2, ActionLevel.HIGH_RISK: 1},
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -----------------------------------------------------
    # PROPOSE
    # -----------------------------------------------------

    def test_propose_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            self.lc.propose("does-not-exist")

    def test_propose_rejects_empty_tool_name(self):
        with self.assertRaises(ValueError):
            self.lc.propose("   ")

    def test_propose_stores_level_and_maps_importance(self):
        saved = self.lc.propose("noop_read")
        self.assertEqual(saved["level"], ActionLevel.READ_ONLY)
        self.assertEqual(saved["importance"], 1)

        saved_high = self.lc.propose("boom")
        self.assertEqual(saved_high["importance"], 5)

    def test_repeated_identical_proposals_get_distinct_ids(self):
        # MemoryEngine dedups byte-identical content -- propose() must
        # embed something that makes each call unique, or the second
        # identical proposal would be silently dropped.
        first = self.lc.propose("noop_read")
        second = self.lc.propose("noop_read")

        self.assertNotEqual(first["id"], second["id"])
        self.assertTrue(first.get("saved", True))
        self.assertTrue(second.get("saved", True))

    def test_invalid_scheduled_for_string_raises(self):
        with self.assertRaises(ValueError):
            self.lc.propose("noop_read", scheduled_for="not-a-date")

    # -----------------------------------------------------
    # READ_ONLY: execute straight from proposed
    # -----------------------------------------------------

    def test_read_only_executes_without_approval(self):
        saved = self.lc.propose("noop_read")
        result = self.lc.execute(saved["id"])

        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["result"], '"ok"')

    def test_read_only_can_also_be_approved_first(self):
        saved = self.lc.propose("noop_read")
        approved = self.lc.approve(saved["id"], approver="aion")
        result = self.lc.execute(approved["id"])

        self.assertEqual(result["status"], "executed")

    # -----------------------------------------------------
    # LOW_RISK: approval gate, self-approval allowed
    # -----------------------------------------------------

    def test_low_risk_cannot_execute_before_approval(self):
        saved = self.lc.propose("noop_low", params={"x": 5})

        with self.assertRaises(ValueError):
            self.lc.execute(saved["id"])

    def test_low_risk_can_be_self_approved(self):
        saved = self.lc.propose("noop_low", params={"x": 5})
        approved = self.lc.approve(saved["id"], approver="aion")

        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approver"], "aion")

        result = self.lc.execute(approved["id"])
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["result"], "10")

    def test_approve_requires_non_empty_approver(self):
        saved = self.lc.propose("noop_low")

        with self.assertRaises(ValueError):
            self.lc.approve(saved["id"], approver="   ")

    def test_cannot_approve_an_already_approved_action(self):
        saved = self.lc.propose("noop_low")
        approved = self.lc.approve(saved["id"], approver="aion")

        with self.assertRaises(ValueError):
            self.lc.approve(approved["id"], approver="aion")

    # -----------------------------------------------------
    # HIGH_RISK: approval gate, self-approval forbidden
    # -----------------------------------------------------

    def test_high_risk_self_approval_by_aion_is_rejected(self):
        saved = self.lc.propose("boom")

        with self.assertRaises(ValueError):
            self.lc.approve(saved["id"], approver="aion")

        with self.assertRaises(ValueError):
            self.lc.approve(saved["id"], approver="AION")  # case-insensitive

    def test_high_risk_can_be_approved_by_a_person(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")

        self.assertEqual(approved["approver"], "Pongsatorn")

    def test_high_risk_cannot_execute_before_approval(self):
        saved = self.lc.propose("boom")

        with self.assertRaises(ValueError):
            self.lc.execute(saved["id"])

    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    def test_reject_requires_reason(self):
        saved = self.lc.propose("noop_low")

        with self.assertRaises(ValueError):
            self.lc.reject(saved["id"], reason="   ", rejector="Pongsatorn")

    def test_reject_only_allowed_from_proposed(self):
        saved = self.lc.propose("noop_low")
        approved = self.lc.approve(saved["id"], approver="aion")

        with self.assertRaises(ValueError):
            self.lc.reject(approved["id"], reason="too late", rejector="x")

    def test_reject_logs_a_lesson_and_blocks_execution(self):
        saved = self.lc.propose("noop_low")
        rejected = self.lc.reject(
            saved["id"], reason="Not needed.", rejector="Pongsatorn"
        )

        self.assertEqual(rejected["status"], "rejected")

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertIn("Rejected action", lessons[0]["content"])

        with self.assertRaises(ValueError):
            self.lc.execute(rejected["id"])

    # -----------------------------------------------------
    # EXECUTE / FAILURE CAPTURE
    # -----------------------------------------------------

    def test_execute_captures_tool_exception_as_failed(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")

        result = self.lc.execute(approved["id"])

        self.assertEqual(result["status"], "failed")
        self.assertIn("kaboom", result["error"])

    def test_execute_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.lc.execute("does-not-exist")

    def test_cannot_execute_an_already_executed_action(self):
        saved = self.lc.propose("noop_read")
        executed = self.lc.execute(saved["id"])

        with self.assertRaises(ValueError):
            self.lc.execute(executed["id"])

    # -----------------------------------------------------
    # RECOVER
    # -----------------------------------------------------

    def test_recover_requires_resolution(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")
        failed = self.lc.execute(approved["id"])

        with self.assertRaises(ValueError):
            self.lc.recover(failed["id"], resolution="   ", evidence=["note"])

    def test_recover_requires_evidence(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")
        failed = self.lc.execute(approved["id"])

        with self.assertRaises(ValueError):
            self.lc.recover(failed["id"], resolution="Escalated.", evidence=[])

    def test_recover_only_allowed_from_failed(self):
        saved = self.lc.propose("noop_read")
        executed = self.lc.execute(saved["id"])

        with self.assertRaises(ValueError):
            self.lc.recover(executed["id"], resolution="x", evidence=["note"])

    def test_recover_supersedes_and_links_evidence(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")
        failed = self.lc.execute(approved["id"])

        recovered = self.lc.recover(
            failed["id"],
            resolution="Escalated to a human, no automatic retry.",
            evidence=[{"id": "ops1", "description": "Ops log."}],
        )

        self.assertEqual(recovered["status"], "recovered")
        self.assertIn("ops1", recovered["related"])
        self.assertIn(failed["id"], recovered["related"])

    # -----------------------------------------------------
    # ABANDON
    # -----------------------------------------------------

    def test_abandon_requires_reason(self):
        saved = self.lc.propose("noop_low")

        with self.assertRaises(ValueError):
            self.lc.abandon(saved["id"], reason="   ")

    def test_abandon_allowed_from_proposed_approved_and_failed(self):
        p1 = self.lc.propose("noop_low")
        self.lc.abandon(p1["id"], reason="r1")

        p2 = self.lc.propose("noop_low")
        approved2 = self.lc.approve(p2["id"], approver="aion")
        self.lc.abandon(approved2["id"], reason="r2")

        p3 = self.lc.propose("boom")
        approved3 = self.lc.approve(p3["id"], approver="Pongsatorn")
        failed3 = self.lc.execute(approved3["id"])
        self.lc.abandon(failed3["id"], reason="r3")

        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 3)

    def test_cannot_abandon_an_executed_action(self):
        saved = self.lc.propose("noop_read")
        executed = self.lc.execute(saved["id"])

        with self.assertRaises(ValueError):
            self.lc.abandon(executed["id"], reason="too late")

    # -----------------------------------------------------
    # KILL SWITCH
    # -----------------------------------------------------

    def test_kill_switch_starts_disengaged(self):
        self.assertFalse(self.lc.kill_switch_engaged())

    def test_engage_and_disengage_require_reason(self):
        with self.assertRaises(ValueError):
            self.lc.engage_kill_switch(reason="   ")

        with self.assertRaises(ValueError):
            self.lc.disengage_kill_switch(reason="")

    def test_kill_switch_blocks_execution_of_any_level(self):
        read_action = self.lc.propose("noop_read")
        low_action = self.lc.propose("noop_low")
        approved_low = self.lc.approve(low_action["id"], approver="aion")

        self.lc.engage_kill_switch(reason="Halt for testing.")
        self.assertTrue(self.lc.kill_switch_engaged())

        with self.assertRaises(RuntimeError):
            self.lc.execute(read_action["id"])

        with self.assertRaises(RuntimeError):
            self.lc.execute(approved_low["id"])

        self.lc.disengage_kill_switch(reason="Resume for testing.")
        self.assertFalse(self.lc.kill_switch_engaged())

        result = self.lc.execute(read_action["id"])
        self.assertEqual(result["status"], "executed")

    def test_repeated_kill_switch_toggles_with_same_reason_dont_collide(self):
        # Same collision risk as propose(): identical reason text
        # would otherwise produce byte-identical content.
        self.lc.engage_kill_switch(reason="Same reason.")
        self.lc.disengage_kill_switch(reason="Same reason.")
        self.lc.engage_kill_switch(reason="Same reason.")

        self.assertTrue(self.lc.kill_switch_engaged())

    # -----------------------------------------------------
    # BUDGETS
    # -----------------------------------------------------

    def test_read_only_budget_is_unlimited(self):
        for _ in range(10):
            saved = self.lc.propose("noop_read")
            result = self.lc.execute(saved["id"])
            self.assertEqual(result["status"], "executed")

    def test_low_risk_budget_enforced(self):
        for _ in range(2):
            saved = self.lc.propose("noop_low")
            approved = self.lc.approve(saved["id"], approver="aion")
            result = self.lc.execute(approved["id"])
            self.assertEqual(result["status"], "executed")

        saved = self.lc.propose("noop_low")
        approved = self.lc.approve(saved["id"], approver="aion")

        with self.assertRaises(ValueError):
            self.lc.execute(approved["id"])

    def test_high_risk_budget_enforced_independently_of_low_risk(self):
        # Use up the LOW_RISK budget (2) -- HIGH_RISK's own budget (1)
        # must be unaffected.
        for _ in range(2):
            saved = self.lc.propose("noop_low")
            approved = self.lc.approve(saved["id"], approver="aion")
            self.lc.execute(approved["id"])

        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")
        result = self.lc.execute(approved["id"])
        self.assertEqual(result["status"], "failed")  # still counts as executed-attempt

        saved2 = self.lc.propose("boom")
        approved2 = self.lc.approve(saved2["id"], approver="Pongsatorn")

        with self.assertRaises(ValueError):
            self.lc.execute(approved2["id"])

    def test_budget_window_rolls_forward(self):
        saved = self.lc.propose("boom")
        approved = self.lc.approve(saved["id"], approver="Pongsatorn")
        self.lc.execute(approved["id"])  # uses up the HIGH_RISK budget of 1

        saved2 = self.lc.propose("boom")
        approved2 = self.lc.approve(saved2["id"], approver="Pongsatorn")

        with self.assertRaises(ValueError):
            self.lc.execute(approved2["id"])

        with mock.patch("brain.tools.datetime") as mock_dt:
            future = datetime.now() + timedelta(
                hours=self.lc.budget_window_hours + 1
            )
            mock_dt.now.return_value = future
            mock_dt.strptime = datetime.strptime

            # The earlier execution is now outside the budget window,
            # so this one must be allowed.
            result = self.lc.execute(approved2["id"])
            self.assertEqual(result["status"], "failed")

    # -----------------------------------------------------
    # SCHEDULING
    # -----------------------------------------------------

    def test_future_scheduled_action_cannot_execute_yet(self):
        future = (datetime.now() + timedelta(hours=1)).isoformat(
            sep=" ", timespec="seconds"
        )
        saved = self.lc.propose("noop_read", scheduled_for=future)

        with self.assertRaises(ValueError):
            self.lc.execute(saved["id"])

    def test_past_scheduled_action_executes(self):
        past = (datetime.now() - timedelta(hours=1)).isoformat(
            sep=" ", timespec="seconds"
        )
        saved = self.lc.propose("noop_read", scheduled_for=past)

        result = self.lc.execute(saved["id"])
        self.assertEqual(result["status"], "executed")

    def test_unscheduled_action_executes_immediately(self):
        saved = self.lc.propose("noop_read")
        self.assertIsNone(saved["scheduled_for"])

        result = self.lc.execute(saved["id"])
        self.assertEqual(result["status"], "executed")

    # -----------------------------------------------------
    # HISTORY / QUERIES
    # -----------------------------------------------------

    def test_history_walks_full_chain(self):
        proposed = self.lc.propose("noop_low", params={"x": 3})
        approved = self.lc.approve(proposed["id"], approver="aion")
        executed = self.lc.execute(approved["id"])

        history = self.lc.history(executed["id"])

        self.assertEqual(
            [entry["id"] for entry in history],
            [proposed["id"], approved["id"], executed["id"]],
        )
        self.assertEqual(
            [entry["status"] for entry in history],
            ["proposed", "approved", "executed"],
        )

    def test_history_of_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.lc.history("does-not-exist")

    def test_actions_filters_by_status_and_respects_limit(self):
        for _ in range(3):
            saved = self.lc.propose("noop_read")
            self.lc.execute(saved["id"])

        self.lc.propose("noop_low")  # left as "proposed"

        executed_only = self.lc.actions(status="executed")
        self.assertEqual(len(executed_only), 3)

        proposed_only = self.lc.actions(status="proposed")
        self.assertEqual(len(proposed_only), 1)

        limited = self.lc.actions(limit=2)
        self.assertEqual(len(limited), 2)

    def test_kill_switch_entries_never_appear_in_actions_listing(self):
        self.lc.engage_kill_switch(reason="test")
        self.lc.disengage_kill_switch(reason="test")

        self.assertEqual(self.lc.actions(), [])


class BuiltinToolsTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="aion_builtin_tools_test_")
        self.memory = MemoryEngine(root=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_only_read_only_tools_are_registered(self):
        registry = build_builtin_tools(self.memory)

        levels = {tool["level"] for tool in registry.list_tools()}
        self.assertEqual(levels, {ActionLevel.READ_ONLY})

    def test_memory_stats_tool_executes_against_real_memory(self):
        self.memory.remember(category="experiences", content="Something happened.")

        registry = build_builtin_tools(self.memory)
        lc = ToolLifecycle(self.memory, registry=registry)

        proposed = lc.propose("memory_stats", params={"category": "experiences"})
        result = lc.execute(proposed["id"])

        self.assertEqual(result["status"], "executed")
        self.assertIn("total", result["result"])

    def test_metacognition_report_tool_executes(self):
        registry = build_builtin_tools(self.memory)
        lc = ToolLifecycle(self.memory, registry=registry)

        proposed = lc.propose("metacognition_report", params={"report": "full"})
        result = lc.execute(proposed["id"])

        self.assertEqual(result["status"], "executed")
        self.assertIn("tool_reliability", result["result"])


if __name__ == "__main__":
    unittest.main()
