"""Offline tests for tools/sync_memory_from_github.py.

Mocks subprocess.run entirely -- this suite must never make a live
git/network call, per the project's rule that unit tests never depend
on a live external service. Never asserts on a real token value; a
placeholder standing in for a PAT is used throughout.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import sync_memory_from_github as sync_memory


class LoadTokenTests(unittest.TestCase):
    def test_environment_variable_takes_priority(self):
        with mock.patch.dict(os.environ, {"MEMORY_REPO_PAT": "env-token"}, clear=False):
            self.assertEqual(sync_memory._load_token(), "env-token")

    def test_reads_from_env_file_when_env_var_absent(self):
        with tempfile.TemporaryDirectory() as root:
            env_file = Path(root) / ".env.memory_sync"
            env_file.write_text(
                "# a comment\nMEMORY_REPO_PAT=file-token\n", encoding="utf-8",
            )
            with mock.patch.object(sync_memory, "ENV_FILE", env_file):
                with mock.patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(sync_memory._load_token(), "file-token")

    def test_returns_none_when_neither_source_has_a_token(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(sync_memory, "ENV_FILE", Path(root) / "missing"):
                with mock.patch.dict(os.environ, {}, clear=True):
                    self.assertIsNone(sync_memory._load_token())


class SyncOnceTests(unittest.TestCase):
    def test_clones_when_no_local_checkout_exists_yet(self):
        with tempfile.TemporaryDirectory() as root:
            clone_dir = Path(root) / "aion-memory-data-sync"
            with mock.patch.object(sync_memory, "CLONE_DIR", clone_dir):
                with mock.patch.object(
                    sync_memory, "_run", return_value=mock.Mock(returncode=0, stderr=""),
                ) as mock_run:
                    result = sync_memory.sync_once("fake-token")

        self.assertTrue(result)
        args = mock_run.call_args.args[0]
        self.assertEqual(args[0:2], ["git", "clone"])
        self.assertIn("fake-token", args[2])

    def test_pulls_when_a_local_checkout_already_exists(self):
        with tempfile.TemporaryDirectory() as root:
            clone_dir = Path(root) / "aion-memory-data-sync"
            (clone_dir / ".git").mkdir(parents=True)
            with mock.patch.object(sync_memory, "CLONE_DIR", clone_dir):
                with mock.patch.object(
                    sync_memory, "_run", return_value=mock.Mock(returncode=0, stderr=""),
                ) as mock_run:
                    result = sync_memory.sync_once("fake-token")

        self.assertTrue(result)
        calls = [call.args[0] for call in mock_run.call_args_list]
        self.assertEqual(calls[0][0:3], ["git", "remote", "set-url"])
        self.assertEqual(calls[1][0:2], ["git", "pull"])

    def test_failure_returns_false_and_never_prints_the_raw_token(self):
        with tempfile.TemporaryDirectory() as root:
            clone_dir = Path(root) / "aion-memory-data-sync"
            with mock.patch.object(sync_memory, "CLONE_DIR", clone_dir):
                with mock.patch.object(
                    sync_memory,
                    "_run",
                    return_value=mock.Mock(
                        returncode=128,
                        stderr="fatal: could not read secret-token-value from url",
                    ),
                ):
                    with mock.patch("builtins.print") as mock_print:
                        result = sync_memory.sync_once("secret-token-value")

        self.assertFalse(result)
        printed = " ".join(str(call) for call in mock_print.call_args_list)
        self.assertNotIn("secret-token-value", printed)
        self.assertIn("***", printed)


if __name__ == "__main__":
    unittest.main()
