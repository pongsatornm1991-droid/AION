"""Regression coverage for the workflow delivery-evidence entry point."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publish_delivery_status", ROOT / "tools" / "publish_delivery_status.py"
)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PublishDeliveryStatusTests(unittest.TestCase):
    def test_uses_the_memory_root_supplied_by_the_workflow(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(os.environ, {"AION_MEMORY_ROOT": root}):
                self.assertEqual(Path(root), publisher.delivery_memory().root)
