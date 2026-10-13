import unittest

from agent.workflow import process_invoice


class TestInvoiceWorkflow(unittest.TestCase):

    def test_abc_invoice_is_processed_and_verified(self):
        result = process_invoice("ABC Company")

        self.assertTrue(result["success"])
        self.assertEqual(
            result["invoice"]["company"],
            "ABC Company",
        )
        self.assertTrue(
            any(
                step.get("step") == "verify"
                and step.get("success") is True
                for step in result["trace"]
            )
        )

    def test_xyz_invoice_is_processed_and_verified(self):
        result = process_invoice("XYZ Corporation")

        self.assertTrue(result["success"])
        self.assertEqual(
            result["invoice"]["company"],
            "XYZ Corporation",
        )

    def test_unknown_company_returns_failure(self):
        result = process_invoice(
            "Company That Does Not Exist"
        )

        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()