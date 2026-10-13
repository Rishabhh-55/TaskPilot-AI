import re
from decimal import Decimal, InvalidOperation


def extract_invoice_fields(content: str) -> dict:
    """
    Extract invoice fields from a text document.

    Returns extracted values and any fields that could not
    be identified.
    """

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Invoice content cannot be empty.")

    patterns = {
        "invoice_number": r"Invoice\s*(?:Number|No\.?|#)\s*:\s*([A-Za-z0-9_-]+)",
        "company": r"Company\s*:\s*(.+)",
        "amount": r"Amount\s*:\s*([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:INR|USD|EUR)?",
        "status": r"Status\s*:\s*([A-Za-z -]+)",
    }

    extracted = {}

    for field, pattern in patterns.items():
        match = re.search(
            pattern,
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if match:
            extracted[field] = match.group(1).strip()
        else:
            extracted[field] = None

    # Convert the amount to a numeric value.
    if extracted["amount"] is not None:
        try:
            amount_text = extracted["amount"].replace(",", "")
            extracted["amount"] = str(Decimal(amount_text))
        except InvalidOperation:
            extracted["amount"] = None

    return extracted


def validate_invoice(invoice: dict) -> dict:
    """Validate the fields extracted from an invoice."""

    errors = []
    required_fields = [
        "invoice_number",
        "company",
        "amount",
        "status",
    ]

    for field in required_fields:
        if not invoice.get(field):
            errors.append(f"Missing or invalid field: {field}")

    amount = None

    if invoice.get("amount"):
        try:
            amount = Decimal(str(invoice["amount"]))

            if not amount.is_finite() or amount < 0:
                errors.append("Amount must be a finite, non-negative number.")

        except InvalidOperation:
            errors.append("Amount must be numeric.")

    valid = not errors

    return {
        "valid": valid,
        "errors": errors,
        "normalized": {
            **invoice,
            "amount": float(amount) if amount is not None and amount.is_finite() and amount >= 0 else None,
        } if valid else None,
    }