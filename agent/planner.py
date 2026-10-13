import json
from typing import Any

from agent.llm_client import LLMClient


class Planner:
    """Creates structured execution plans using the local LLM."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    def create_plan(
        self,
        user_request: str,
        available_tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Convert a user request into a structured plan.

        The planner decides which tools are needed but does not
        execute them.
        """

        tools_description = json.dumps(
            available_tools,
            indent=2,
            ensure_ascii=False,
        )

        system_prompt = """
You are the planning component of TaskPilot-AI,
an autonomous AI agent.

Your responsibility is to convert the user's request into
a safe, clear, executable sequence of steps.

Rules:
1. Use only the tools provided in AVAILABLE TOOLS.
2. Never invent tools or tool arguments.
3. Break complex requests into small, logical steps.
4. Each step must specify a tool and its arguments.
5. Include verification steps when the user explicitly requests verification.
6. Do not claim that an action has already been executed.
7. If the request cannot be completed with the available tools,
   explain what capability is missing.
8. Avoid unnecessary or redundant steps.
9. Match each argument to the exact meaning specified by the tool.
10. get_invoice requires the exact invoice_number, NOT a company name.
11. Never pass a company name, such as "XYZ Corporation", as
    the invoice_number argument to get_invoice.
12. If the user provides a company name but no invoice number,
    first use search_invoices or list_invoices to find matching
    invoice records.
13. Only call get_invoice after obtaining the exact invoice_number
    from the user's request or a previous tool result.
14. If no matching invoice is found, explain that no matching
    invoice was found. Never invent an invoice number.
15. If process_invoice has already returned an invoice record,
    reuse its invoice_number when calling get_invoice.
16. If the user asks whether a company appears in the database,
    list_invoices can establish this by checking the company field.
17. Do not add get_invoice after process_invoice and list_invoices
    if those results already satisfy the user's request.
18. Never invent a value for a tool argument when the value is
    unavailable from the request or previous results.
19. Plan only the steps needed to satisfy the user's request.

Return only a valid JSON object using this structure:

{
  "goal": "A short description of the intended outcome",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "arguments": {},
      "purpose": "Why this step is needed"
    }
  ],
  "success_criteria": [
    "A condition that must be true for the task to be complete"
  ]
}

If no available tool can perform the requested task, return an
empty steps array and explain the limitation in success_criteria.
"""

        user_prompt = f"""
AVAILABLE TOOLS:
{tools_description}

USER REQUEST:
{user_request}

Create the execution plan as valid JSON.
"""

        response = self.llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
            max_tokens=2048,
        )

        return self._parse_plan(response, available_tools)

    @staticmethod
    def _parse_plan(
        response: str,
        available_tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Parse and validate the plan returned by the LLM."""

        if not isinstance(response, str) or not response.strip():
            raise ValueError("The model returned an empty response.")

        # First, try parsing the response exactly as returned.
        try:
            plan = json.loads(response)
        except json.JSONDecodeError:
            # Some models wrap JSON in Markdown code fences
            # or add a short explanation around the JSON.
            text = response.strip()

            if text.startswith("```"):
                lines = text.splitlines()

                if lines and lines[0].startswith("```"):
                    lines = lines[1:]

                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]

                text = "\n".join(lines).strip()

                if text.lower().startswith("json"):
                    text = text[4:].lstrip()

            try:
                plan = json.loads(text)
            except json.JSONDecodeError:
                # If there is surrounding text, extract the outermost
                # JSON object and attempt to parse it.
                start = text.find("{")
                end = text.rfind("}")

                if start == -1 or end <= start:
                    raise ValueError(
                        "The model did not return a valid JSON object. "
                        "The plan cannot be executed safely."
                    )

                try:
                    plan = json.loads(text[start:end + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "The model did not return valid JSON. "
                        "The plan cannot be executed safely."
                    ) from exc

        if not isinstance(plan, dict):
            raise ValueError("The plan must be a JSON object.")

        if not isinstance(plan.get("goal"), str):
            raise ValueError("The plan is missing a valid goal.")

        steps = plan.get("steps")

        if not isinstance(steps, list):
            raise ValueError("The plan must contain a steps list.")

        if not isinstance(plan.get("success_criteria"), list):
            raise ValueError(
                "The plan must contain success_criteria."
            )

        allowed_tools = {
            tool.get("name")
            for tool in available_tools
            if isinstance(tool, dict)
        }

        if not plan["goal"].strip():
            raise ValueError("Plan goal cannot be empty.")

        if not plan["success_criteria"]:
            raise ValueError("Plan must include success criteria.")

        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError(
                    f"Step {index} must be a JSON object."
                )

            tool_name = step.get("tool")

            if not isinstance(tool_name, str) or tool_name not in allowed_tools:
                raise ValueError(
                    f"Step {index} uses an unavailable tool: "
                    f"{tool_name!r}"
                )

            arguments = step.get("arguments")

            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Step {index} must contain an arguments object."
                )

            if not isinstance(step.get("purpose"), str) or not step["purpose"].strip():
                raise ValueError(
                    f"Step {index} must specify a non-empty purpose."
                )

            if tool_name == "get_invoice":
                invoice_number = arguments.get("invoice_number")

                if not isinstance(invoice_number, str) or not invoice_number.strip():
                    raise ValueError(
                        f"Step {index}: get_invoice requires a "
                        "non-empty invoice_number string."
                    )

                if " " in invoice_number.strip():
                    raise ValueError(
                        f"Step {index}: invoice_number appears to contain "
                        "a company name or description instead of an ID."
                    )

        return plan