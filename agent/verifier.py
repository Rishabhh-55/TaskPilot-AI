import re
from typing import Any


class Verifier:

    def verify_execution(
        self,
        plan: dict,
        results: list[dict],
    ) -> dict:

        expected_steps = plan.get("steps", [])

        # A tool can return success=False inside its result,
        # even if the executor's outer result says success=True.
        def step_succeeded(result: dict) -> bool:
            if result.get("success") is not True:
                return False

            output = result.get("result")

            if isinstance(output, dict) and output.get("success") is False:
                return False

            return True

        successful_steps = sum(
            1 for result in results if step_succeeded(result)
        )

        failed_steps = [
            result for result in results
            if not step_succeeded(result)
        ]

        all_steps_executed = len(results) == len(expected_steps)

        all_steps_succeeded = (
            all_steps_executed
            and successful_steps == len(expected_steps)
        )

        execution_evidence = []
        semantic_checks = []

        # Read the arguments from the plan rather than trying to
        # extract the company name from a potentially long goal.
        process_step = next(
            (
                step for step in expected_steps
                if isinstance(step, dict)
                and step.get("tool") == "process_invoice"
            ),
            None,
        )

        if process_step is not None:
            requested_company = (
                process_step.get("arguments", {}).get("company", "")
            )

            process_result = next(
                (
                    result for result in results
                    if result.get("tool") == "process_invoice"
                ),
                None,
            )

            output = (
                process_result.get("result", {})
                if process_result else {}
            )

            if not isinstance(output, dict):
                output = {}

            trace = output.get("trace", [])

            if not isinstance(trace, list):
                trace = []

            successful_trace_steps = {
                item.get("step")
                for item in trace
                if isinstance(item, dict)
                and item.get("success") is True
            }

            invoice = output.get("invoice", {})

            if not isinstance(invoice, dict):
                invoice = {}

            workflow_succeeded = (
                process_result is not None
                and step_succeeded(process_result)
                and output.get("success") is True
            )

            semantic_checks.append({
                "check": "Invoice processing workflow completed",
                "passed": workflow_succeeded,
            })

            company_matches = (
                bool(requested_company)
                and invoice.get("company", "").strip().casefold()
                == requested_company.strip().casefold()
            )

            semantic_checks.append({
                "check": "Saved invoice belongs to the requested company",
                "passed": company_matches,
                "requested_company": requested_company,
                "saved_company": invoice.get("company"),
            })

            record_verified = (
                "verify" in successful_trace_steps
                and bool(invoice.get("invoice_number"))
                and invoice.get("id") is not None
            )

            semantic_checks.append({
                "check": "Saved database record was independently verified",
                "passed": record_verified,
                "invoice_number": invoice.get("invoice_number"),
                "database_id": invoice.get("id"),
            })

            required_trace_steps = {
                "search",
                "read",
                "extract",
                "validate",
            }

            # Either a new record was saved or an identical existing
            # record was found. Both are valid idempotent outcomes.
            save_or_duplicate_confirmed = (
                "save" in successful_trace_steps
                or "duplicate_check" in successful_trace_steps
            )

            trace_complete = (
                required_trace_steps.issubset(successful_trace_steps)
                and save_or_duplicate_confirmed
                and "verify" in successful_trace_steps
            )

            semantic_checks.append({
                "check": "All invoice processing stages completed",
                "passed": trace_complete,
                "completed_stages": sorted(successful_trace_steps),
            })

            execution_evidence.append({
                "tool": "process_invoice",
                "company": invoice.get("company"),
                "invoice_number": invoice.get("invoice_number"),
                "amount": invoice.get("amount"),
                "status": invoice.get("status"),
                "database_id": invoice.get("id"),
                "already_processed": output.get("already_processed", False),
                "trace": trace,
            })
            # Verify that list_invoices actually contains
            # the company requested in the processing step.
            list_step = next(
                (
                    step for step in expected_steps
                    if isinstance(step, dict)
                    and step.get("tool") == "list_invoices"
                ),
                None,
            )

            if list_step is not None:
                list_result = next(
                    (
                        result for result in results
                        if result.get("tool") == "list_invoices"
                    ),
                    None,
                )

                list_output = (
                    list_result.get("result")
                    if list_result is not None
                    else None
                )

                if isinstance(list_output, dict):
                    invoices = list_output.get("invoices", [])
                else:
                    invoices = list_output

                if not isinstance(invoices, list):
                    invoices = []

                company_found = any(
                    isinstance(item, dict)
                    and isinstance(item.get("company"), str)
                    and item["company"].strip().casefold()
                    == requested_company.strip().casefold()
                    for item in invoices
                )

                semantic_checks.append({
                    "check": (
                        "Invoice listing contains the requested company"
                    ),
                    "passed": (
                        list_result is not None
                        and step_succeeded(list_result)
                        and company_found
                    ),
                    "requested_company": requested_company,
                    "company_found": company_found,
                })    

        else:
            # Preserve the original search/read verification behavior
            # for tasks that do not use process_invoice.
            for result in results:
                if not step_succeeded(result):
                    continue

                tool_name = result.get("tool")
                tool_output = result.get("result")

                if tool_name == "read_file" and isinstance(
                    tool_output, dict
                ):
                    execution_evidence.append({
                        "tool": tool_name,
                        "document": tool_output.get("name", ""),
                        "content": tool_output.get("content", ""),
                    })

                elif tool_name == "search_files":
                    execution_evidence.append({
                        "tool": tool_name,
                        "result_count": (
                            len(tool_output)
                            if isinstance(tool_output, list)
                            else 0
                        ),
                    })

            goal = plan.get("goal", "")
            goal_lower = goal.lower()

            company_match = re.search(
                r"\bfor\s+(.+?)(?:\s+and\s+|\s*$)",
                goal,
                flags=re.IGNORECASE,
            )

            requested_entity = None

            if company_match:
                requested_entity = re.sub(
                    r"\b(invoice|document|file|contents|details)\b",
                    "",
                    company_match.group(1),
                    flags=re.IGNORECASE,
                ).strip().lower()

            if "invoice" in goal_lower:
                invoice_documents = [
                    item for item in execution_evidence
                    if item["tool"] == "read_file"
                    and "invoice" in item["document"].lower()
                ]

                semantic_checks.append({
                    "check": "An invoice document was read",
                    "passed": bool(invoice_documents),
                    "documents_checked": [
                        item["document"] for item in invoice_documents
                    ],
                })

            if requested_entity:
                read_documents = [
                    item for item in execution_evidence
                    if item["tool"] == "read_file"
                ]

                company_found = any(
                    requested_entity in item["content"].lower()
                    for item in read_documents
                )

                semantic_checks.append({
                    "check": "Requested company appears in document",
                    "passed": company_found,
                    "entity": requested_entity,
                    "documents_checked": [
                        item["document"] for item in read_documents
                    ],
                })

        semantic_checks_passed = all(
            check["passed"] is True
            for check in semantic_checks
        )

        verified = (
            all_steps_succeeded
            and semantic_checks_passed
        )

        if verified:
            message = "Execution succeeded and semantic checks passed."
        elif not all_steps_succeeded:
            message = "The plan did not complete successfully."
        else:
            message = (
                "Execution completed, but semantic verification failed."
            )

        return {
            "verified": verified,
            "expected_steps": len(expected_steps),
            "executed_steps": len(results),
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "semantic_checks": semantic_checks,
            "evidence": execution_evidence,
            "message": message,
        }