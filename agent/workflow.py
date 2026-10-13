from tools.files import search_files, read_file
from tools.invoices import create_invoice, get_invoice

from agent.invoice_processor import (
    extract_invoice_fields,
    validate_invoice,
)


def process_invoice(company: str) -> dict:
    """Find, extract, validate, save, and verify an invoice."""

    trace = []

    try:
        # 1. Search for documents
        matches = search_files(company)

        if not matches:
            return {
                "success": False,
                "message": f"No invoice document found for {company}.",
                "trace": trace,
            }

        # Select the best matching document.
        # If multiple documents have the same strongest match,
        # stop rather than choosing arbitrarily.
        matches = sorted(
            matches,
            key=lambda item: item.get("match_count", 0),
            reverse=True,
        )

        if (
            len(matches) > 1
            and matches[0].get("match_count", 0)
            == matches[1].get("match_count", 0)
        ):
            return {
                "success": False,
                "message": (
                    "Multiple documents have equally strong matches. "
                    "Please specify the invoice more precisely."
                ),
                "matches": matches,
                "trace": trace,
            }

        document_path = matches[0]["path"]

        trace.append({
            "step": "search",
            "success": True,
            "document": document_path,
        })

        # 2. Read the selected document
        document = read_file(document_path)

        if not isinstance(document, dict) or "content" not in document:
            return {
                "success": False,
                "message": "Could not read the invoice document.",
                "error": document,
                "trace": trace,
            }

        content = document["content"]

        trace.append({
            "step": "read",
            "success": True,
            "document": document_path,
        })

        # 3. Extract invoice fields
        extracted = extract_invoice_fields(content)

        trace.append({
            "step": "extract",
            "success": True,
            "fields": extracted,
        })

        # 4. Validate extracted fields
        validation = validate_invoice(extracted)

        if not validation["valid"]:
            return {
                "success": False,
                "message": "Invoice validation failed.",
                "errors": validation["errors"],
                "trace": trace,
            }

        invoice = validation["normalized"]

        # 5. Verify the requested company matches the document.
        # Use exact matching to avoid processing the wrong company.
        if invoice["company"].casefold() != company.strip().casefold():
            return {
                "success": False,
                "message": "The invoice company does not match the request.",
                "requested_company": company,
                "extracted_company": invoice["company"],
                "trace": trace,
            }

        trace.append({
            "step": "validate",
            "success": True,
        })

        # 6. Save to the database
        save_result = create_invoice(
            invoice_number=invoice["invoice_number"],
            company=invoice["company"],
            amount=invoice["amount"],
            status=invoice["status"],
            source_document=document_path,
        )

        if not save_result.get("success"):

            # If the invoice already exists, check whether its data matches.
            if save_result.get("error") == "duplicate_invoice":
                existing = save_result.get("existing_invoice", {})

                expected_fields = {
                    "invoice_number": invoice["invoice_number"],
                    "company": invoice["company"],
                    "amount": float(invoice["amount"]),
                    "status": invoice["status"],
                    "source_document": document_path,
                }

                conflicts = []

                for field, expected_value in expected_fields.items():
                    actual_value = existing.get(field)

                    if field == "amount":
                        matches = (
                            actual_value is not None
                            and float(actual_value) == float(expected_value)
                        )
                    else:
                        matches = (
                            str(actual_value).casefold()
                            == str(expected_value).casefold()
                        )

                    if not matches:
                        conflicts.append(field)

                if conflicts:
                    return {
                        "success": False,
                        "message": (
                            "An invoice with this number already exists, "
                            "but its details conflict with the document."
                        ),
                        "conflicting_fields": conflicts,
                        "existing_invoice": existing,
                        "trace": trace,
                    }

                trace.append({
                    "step": "duplicate_check",
                    "success": True,
                    "message": "Existing invoice matches the document.",
                })

                verification = get_invoice(invoice["invoice_number"])

                if not verification.get("success"):
                    return {
                        "success": False,
                        "message": "Could not verify the existing invoice.",
                        "trace": trace,
                    }

                trace.append({
                    "step": "verify",
                    "success": True,
                    "invoice_number": invoice["invoice_number"],
                })

                return {
                    "success": True,
                    "message": (
                        "Invoice was already processed. "
                        "Existing record matches the document; no duplicate created."
                    ),
                    "invoice": verification["invoice"],
                    "already_processed": True,
                    "trace": trace,
                }

            return {
                "success": False,
                "message": save_result.get(
                    "message", "Invoice could not be saved."
                ),
                "save_result": save_result,
                "trace": trace,
            }

        trace.append({
            "step": "save",
            "success": True,
            "invoice_number": invoice["invoice_number"],
        })

        # 7. Retrieve the record independently
        verification = get_invoice(invoice["invoice_number"])

        if not verification.get("success"):
            return {
                "success": False,
                "message": "Could not retrieve the saved invoice.",
                "trace": trace,
            }

        saved_invoice = verification["invoice"]

        expected = {
            "invoice_number": invoice["invoice_number"],
            "company": invoice["company"],
            "amount": invoice["amount"],
            "status": invoice["status"],
            "source_document": document_path,
        }

        mismatches = []

        for field, expected_value in expected.items():
            actual_value = saved_invoice[field]

            if field == "amount":
                matches_value = float(actual_value) == float(expected_value)
            else:
                matches_value = (
                    str(actual_value).casefold()
                    == str(expected_value).casefold()
                )

            if not matches_value:
                mismatches.append(field)

        if mismatches:
            return {
                "success": False,
                "message": "Saved invoice verification failed.",
                "mismatched_fields": mismatches,
                "saved_invoice": saved_invoice,
                "trace": trace,
            }

        trace.append({
            "step": "verify",
            "success": True,
            "invoice_number": invoice["invoice_number"],
        })

        return {
            "success": True,
            "message": "Invoice processed and independently verified.",
            "invoice": saved_invoice,
            "trace": trace,
        }

    except Exception as exc:
        return {
            "success": False,
            "message": "An unexpected error occurred while processing the invoice.",
            "error": str(exc),
            "trace": trace,
        }