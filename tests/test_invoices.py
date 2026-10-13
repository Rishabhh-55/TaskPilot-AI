import unittest

from agent.executor import Executor
from agent.verifier import Verifier
from tools.files import search_files, read_file


class TestTaskPilotAgent(unittest.TestCase):

    def setUp(self):
        self.tools = {
            "search_files": search_files,
            "read_file": read_file,
        }

        self.executor = Executor(self.tools)
        self.verifier = Verifier()

    def test_search_finds_invoice(self):
        result = search_files("ABC Company invoice")

        self.assertTrue(
            any(
                item["name"] == "invoice_demo.txt"
                for item in result
            ),
            "The sample invoice should be found.",
        )

    def test_read_existing_invoice(self):
        result = read_file("invoice_demo.txt")

        self.assertIn("ABC Company", result["content"])
        self.assertIn("INV-1001", result["content"])

    def test_missing_file_returns_failure(self):
        result = self.executor.execute_step({
            "tool": "read_file",
            "arguments": {
                "path": "this_file_does_not_exist.txt"
            },
        })

        self.assertFalse(result["success"])

    def test_unknown_tool_returns_failure(self):
        result = self.executor.execute_step({
            "tool": "delete_everything",
            "arguments": {},
        })

        self.assertFalse(result["success"])

    def test_verifier_detects_wrong_company(self):
        plan = {
            "goal": "Find and read the invoice document for ABC Company",
            "steps": [
                {
                    "step": 1,
                    "tool": "read_file",
                    "arguments": {"path": "invoice_demo.txt"},
                }
            ],
        }

        results = [
            {
                "success": True,
                "tool": "read_file",
                "result": {
                    "name": "wrong_invoice.txt",
                    "content": "Company: XYZ Company",
                },
            }
        ]

        verification = self.verifier.verify_execution(plan, results)

        self.assertFalse(verification["verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)