from agent.planner import Planner
from agent.executor import Executor
from agent.verifier import Verifier
from tools.files import search_files, read_file
from agent.workflow import process_invoice
from tools.invoices import (
    create_invoice,
    get_invoice,
    list_invoices,
)

AVAILABLE_TOOLS = [
    {
        "name": "search_files",
        "description": (
            "Search supported documents for words in their "
            "filename or contents."
        ),
        "arguments": {
            "query": "string",
        },
    },
    {
        "name": "read_file",
        "description": "Read a supported document from the documents folder.",
        "arguments": {
            "path": "string",
        },
    },
    {
        "name": "create_invoice",
        "description": (
            "Create an invoice record in the local company database. "
            "Requires invoice_number, company, amount, status, "
            "and source_document."
        ),
        "arguments": {
            "invoice_number": "string",
            "company": "string",
            "amount": "number",
            "status": "string",
            "source_document": "string",
        },
    },
    {
        "name": "get_invoice",
        "description": (
            "Retrieve a saved invoice by its exact invoice number."
        ),
        "arguments": {
            "invoice_number": "string",
        },
    },
    {
        "name": "list_invoices",
        "description": (
            "List all invoice records stored in the local company database."
        ),
        "arguments": {},
    },
    {
        "name": "process_invoice",
        "description": (
            "Process an invoice for a specified company. "
            "Search documents, extract invoice fields, validate the data, "
            "save the invoice to SQLite, and verify the saved record. "
            "Requires the exact company name."
        ),
        "arguments": {
            "company": "string"
        },
    },
]

REGISTERED_TOOLS = {
    "search_files": search_files,
    "read_file": read_file,
    "create_invoice": create_invoice,
    "get_invoice": get_invoice,
    "list_invoices": list_invoices,
    "process_invoice": process_invoice,
}

class TaskPilotAgent:
    def __init__(self):
        self.planner = Planner()
        self.executor = Executor(
            REGISTERED_TOOLS,
            {
                "search_files": {
                    "required": ["query"],
                    "allowed": ["query"],
                },
                "read_file": {
                    "required": ["path"],
                    "allowed": ["path"],
                },
                "create_invoice": {
                    "required": [
                        "invoice_number",
                        "company",
                        "amount",
                        "status",
                        "source_document",
                    ],
                    "allowed": [
                        "invoice_number",
                        "company",
                        "amount",
                        "status",
                        "source_document",
                    ],
                },
                "get_invoice": {
                    "required": ["invoice_number"],
                    "allowed": ["invoice_number"],
                },
                "list_invoices": {
                    "required": [],
                    "allowed": [],
                },
                "process_invoice": {
                    "required": ["company"],
                    "allowed": ["company"],
                },
            },
        )
        self.verifier = Verifier()

    def run(self, user_request: str) -> dict:
        if not user_request.strip():
            raise ValueError("Please enter a task.")

        # 1. Ask the LLM to create a plan.
        plan = self.planner.create_plan(
            user_request=user_request,
            available_tools=AVAILABLE_TOOLS,
        )

        # 2. Execute the plan.
        results = self.executor.execute_plan(plan)

        # 3. Verify the outcome.
        verification = self.verifier.verify_execution(
            plan,
            results,
        )

        return {
            "goal": plan.get("goal"),
            "plan": plan,
            "results": results,
            "verification": verification,
        }