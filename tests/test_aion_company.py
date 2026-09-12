import tempfile
import unittest

from brain.aion_company import AionCompany
from brain.memory import MemoryEngine


class AionCompanyTests(unittest.TestCase):
    def test_company_has_clear_ceo_and_department_handoffs(self):
        with tempfile.TemporaryDirectory() as root:
            board = AionCompany(MemoryEngine(root), root).board([], [])
            self.assertIn("AION", board["leadership"]["ceo"])
            self.assertGreaterEqual(len(board["departments"]), 9)
            self.assertTrue(all(item["handoff"] for item in board["departments"]))
            self.assertIn("เผยแพร่ผลงานสาธารณะ", board["boundary"])
            self.assertTrue(any(item["name"] == "Dev Agent" for item in board["agents"]))
