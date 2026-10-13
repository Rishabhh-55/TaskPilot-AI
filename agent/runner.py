from agent.planner import Planner
from agent.executor import Executor
from agent.verifier import Verifier
from tools.files import search_files, read_file, list_files
from agent.workflow import (
    process_invoice,
    extract_invoice_data,
    verify_invoice,
)
from tools.invoices import (
    create_invoice,
    get_invoice,
    list_invoices,
    search_invoices,
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
    {
        "name": "list_files",
        "description": "List supported documents in the documents directory.",
        "arguments": {},
    },
    {
        "name": "extract_invoice_data",
        "description": "Extract invoice fields from document text.",
        "arguments": {
            "content": "string",
        },
    },
    {
        "name": "search_invoices",
        "description": "Search saved invoices by invoice number or company name.",
        "arguments": {
            "query": "string",
        },
    },
    {
        "name": "verify_invoice",
        "description": "Check whether an invoice exists in the database using its exact invoice number.",
        "arguments": {
            "invoice_number": "string",
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
    "list_files": list_files,
    "extract_invoice_data": extract_invoice_data,
    "search_invoices": search_invoices,
    "verify_invoice": verify_invoice,
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
                "list_files": {
                    "required": [],
                    "allowed": [],
                },
                "extract_invoice_data": {
                    "required": ["content"],
                    "allowed": ["content"],
                },
                "search_invoices": {
                    "required": ["query"],
                    "allowed": ["query"],
                },
                "verify_invoice": {
                    "required": ["invoice_number"],
                    "allowed": ["invoice_number"],
                },
            },
        )
        self.verifier = Verifier()

    def plan(self, user_request: str) -> dict:
        """Generate a plan without executing any tools."""
        if not isinstance(user_request, str) or not user_request.strip():
            raise ValueError("Please enter a task.")

        plan = self.planner.create_plan(
            user_request=user_request,
            available_tools=AVAILABLE_TOOLS,
        )

        return {
            "goal": plan.get("goal"),
            "plan": plan,
        }

    def execute_approved_plan(self, plan: dict) -> dict:
        """Execute a plan only after explicit user approval."""
        if not isinstance(plan, dict):
            raise ValueError("The approved plan must be a dictionary.")

        if not isinstance(plan.get("steps"), list) or not plan["steps"]:
            raise ValueError("The plan must contain at least one step.")

        # Reject plans that use tools outside the registered tool list.
        for step in plan["steps"]:
            if (
                not isinstance(step, dict)
                or step.get("tool") not in REGISTERED_TOOLS
                or not isinstance(step.get("arguments"), dict)
            ):
                raise ValueError("The plan contains an invalid tool step.")

        results = self.executor.execute_plan(plan)

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

    def run(self, user_request: str) -> dict:
        """Compatibility method: plan and execute immediately."""
        planned = self.plan(user_request)
        return self.execute_approved_plan(planned["plan"])

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