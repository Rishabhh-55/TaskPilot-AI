import unittest

from agent.planner import Planner


AVAILABLE_TOOLS = [
    {
        "name": "get_invoice",
        "description": "Retrieve a saved invoice by its exact invoice number.",
        "arguments": {
            "invoice_number": "string",
        },
    },
    {
        "name": "process_invoice",
        "description": "Process an invoice for a specified company.",
        "arguments": {
            "company": "string",
        },
    },
    {
        "name": "list_invoices",
        "description": "List all saved invoices.",
        "arguments": {},
    },
]


class TestPlanner(unittest.TestCase):

    def test_rejects_company_name_as_invoice_number(self):
        response = """
        {
            "goal": "Verify XYZ Corporation",
            "steps": [
                {
                    "step": 1,
                    "tool": "get_invoice",
                    "arguments": {
                        "invoice_number": "XYZ Corporation"
                    },
                    "purpose": "Find the company invoice"
                }
            ],
            "success_criteria": [
                "The invoice exists"
            ]
        }
        """

        with self.assertRaises(ValueError):
            Planner._parse_plan(response, AVAILABLE_TOOLS)


if __name__ == "__main__":
    unittest.main()