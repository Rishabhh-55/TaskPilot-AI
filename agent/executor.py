import re
from typing import Any, Callable


class Executor:
    """Executes validated tool calls and resolves previous-step results."""

    def __init__(
        self,
        tools: dict[str, Callable],
        tool_schemas: dict[str, dict] | None = None,
    ):
        self.tools = tools
        self.tool_schemas = tool_schemas or {}

    def _resolve_placeholders(
        self,
        value: Any,
        previous_results: list[dict],
    ) -> Any:
        """Resolve references to results from earlier execution steps."""

        if not isinstance(value, str):
            return value

        # Support the placeholder Gemini generated:
        # {{step_1.results[0].path}}
        match = re.fullmatch(
            r"\{\{\s*step_(\d+)\.results\[(\d+)\]\.([a-zA-Z_]\w*)\s*\}\}",
            value,
        )

        if match:
            step_number = int(match.group(1))
            result_index = int(match.group(2))
            field_name = match.group(3)

            if step_number < 1 or step_number > len(previous_results):
                raise ValueError(
                    f"Cannot resolve '{value}': referenced step "
                    "has not executed successfully."
                )

            step_result = previous_results[step_number - 1]

            if not step_result.get("success"):
                raise ValueError(
                    f"Cannot resolve '{value}': referenced step failed."
                )

            tool_result = step_result.get("result")

            if not isinstance(tool_result, list):
                raise ValueError(
                    f"Cannot resolve '{value}': previous result "
                    "is not a list."
                )

            if result_index >= len(tool_result):
                raise ValueError(
                    f"Cannot resolve '{value}': result index "
                    "is out of range."
                )

            item = tool_result[result_index]

            if not isinstance(item, dict) or field_name not in item:
                raise ValueError(
                    f"Cannot resolve '{value}': field "
                    f"'{field_name}' was not found."
                )

            return item[field_name]

        # Preserve support for the older generic placeholder format.
        if (
            value.startswith("<")
            and value.endswith(">")
            and (
                "search" in value.lower()
                or "result" in value.lower()
            )
        ):
            searches = [
                result
                for result in previous_results
                if result.get("success") is True
                and result.get("tool") == "search_files"
            ]

            if not searches:
                raise ValueError(
                    "Cannot resolve placeholder: "
                    "no successful search result is available."
                )

            search_results = searches[-1].get("result")

            if not isinstance(search_results, list) or not search_results:
                raise ValueError("The previous search returned no results.")

            best_match = max(
                (
                    item for item in search_results
                    if isinstance(item, dict) and item.get("path")
                ),
                key=lambda item: (
                    item.get("match_ratio", 0),
                    item.get("match_count", 0),
                ),
                default=None,
            )

            if best_match is None:
                raise ValueError("The search result has no valid path.")

            return best_match["path"]

        return value

    def execute_step(
        self,
        step: dict[str, Any],
        previous_results: list[dict] | None = None,
    ) -> dict[str, Any]:

        previous_results = previous_results or []

        if not isinstance(step, dict):
            return {
                "success": False,
                "error": "Step must be a dictionary.",
            }

        tool_name = step.get("tool")
        arguments = step.get("arguments")

        if not isinstance(tool_name, str) or tool_name not in self.tools:
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name!r}",
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "tool": tool_name,
                "error": "Tool arguments must be a dictionary.",
            }

        arguments = arguments.copy()

        try:
            arguments = {
                key: self._resolve_placeholders(value, previous_results)
                for key, value in arguments.items()
            }
        except (ValueError, TypeError, IndexError) as exc:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(exc),
            }

        schema = self.tool_schemas.get(tool_name)

        if schema:
            required = schema.get("required", [])
            allowed = schema.get("allowed", [])

            missing = [key for key in required if key not in arguments]
            unexpected = [key for key in arguments if key not in allowed]

            if missing:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": f"Missing required arguments: {missing}",
                }

            if unexpected:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": f"Unexpected arguments: {unexpected}",
                }

        try:
            result = self.tools[tool_name](**arguments)

            if isinstance(result, dict) and result.get("success") is False:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": result.get(
                        "message",
                        result.get("error", "Tool execution failed."),
                    ),
                    "result": result,
                }

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
            }

        except Exception as exc:
            return {
                "success": False,
                "tool": tool_name,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def execute_plan(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(plan, dict):
            return [{
                "success": False,
                "error": "Plan must be a dictionary.",
            }]

        steps = plan.get("steps", [])

        if not isinstance(steps, list):
            return [{
                "success": False,
                "error": "Plan steps must be a list.",
            }]

        results = []

        for step in steps:
            result = self.execute_step(step, previous_results=results)

            if not result["success"]:
                error_message = result.get("error", "").lower()

                permanent_failure_phrases = [
                    "previous search returned no results",
                    "no successful search result is available",
                    "unknown tool",
                    "missing required arguments",
                    "unexpected arguments",
                    "unsupported file type",
                    "access outside the documents directory is prohibited",
                    "document not found",
                    "search query cannot be empty",
                    "cannot resolve",
                    "result index is out of range",
                ]

                is_permanent_failure = any(
                    phrase in error_message
                    for phrase in permanent_failure_phrases
                )

                if is_permanent_failure:
                    result["retry_attempted"] = False
                else:
                    retry_result = self.execute_step(
                        step,
                        previous_results=results,
                    )
                    retry_result["retry_attempted"] = True
                    result = retry_result
            else:
                result["retry_attempted"] = False

            results.append(result)

            if not result["success"]:
                break

        return results