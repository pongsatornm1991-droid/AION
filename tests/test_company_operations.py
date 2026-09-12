import unittest
from pathlib import Path

from brain.company_operations import CompanyOperations


class CompanyOperationsTests(unittest.TestCase):
    def test_every_department_is_bound_to_real_code_and_a_workflow(self):
        audit = CompanyOperations(Path(__file__).resolve().parents[1]).audit()
        self.assertEqual("operational", audit["status"])
        self.assertEqual(13, len(audit["departments"]))
        self.assertTrue(all(item["modules"] and item["workflows"] for item in audit["departments"]))
