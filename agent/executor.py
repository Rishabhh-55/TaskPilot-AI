from typing import Any, Callable


class Executor:
    def __init__(
        self,
        tools: dict[str, Callable],
        tool_schemas: dict[str, dict] | None = None,
    ):
        self.tools = tools
        self.tool_schemas = tool_schemas or {}

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

        # Validate tool name.
        if not isinstance(tool_name, str) or tool_name not in self.tools:
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name!r}",
            }

        # Validate argument structure.
        if not isinstance(arguments, dict):
            return {
                "success": False,
                "tool": tool_name,
                "error": "Tool arguments must be a dictionary.",
            }

        arguments = arguments.copy()

        # Resolve file-path placeholders using earlier search results.
        for key, value in list(arguments.items()):
            if not isinstance(value, str):
                continue

            if not (
                value.startswith("<")
                and value.endswith(">")
                and (
                    "search" in value.lower()
                    or "result" in value.lower()
                )
            ):
                continue

            successful_searches = [
                result
                for result in previous_results
                if result.get("success") is True
                and result.get("tool") == "search_files"
            ]

            if not successful_searches:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": (
                        f"Cannot resolve '{key}': "
                        "no successful search result is available."
                    ),
                }

            search_results = successful_searches[-1].get("result")

            if not isinstance(search_results, list) or not search_results:
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": "The previous search returned no results.",
                }

            ranked_results = sorted(
                search_results,
                key=lambda item: (
                    item.get("match_ratio", 0),
                    item.get("match_count", 0),
                ) if isinstance(item, dict) else (0, 0),
                reverse=True,
            )

            best_match = ranked_results[0]

            if not isinstance(best_match, dict) or not best_match.get("path"):
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": "The best search result has no valid path.",
                }

            arguments[key] = best_match["path"]

        # Validate required and allowed arguments.
        schema = self.tool_schemas.get(tool_name)

        if schema:
            required = schema.get("required", [])
            allowed = schema.get("allowed", [])

            missing = [
                key for key in required
                if key not in arguments
            ]

            unexpected = [
                key for key in arguments
                if key not in allowed
            ]

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

        # Execute the tool.
                # Execute the tool.
        try:
            result = self.tools[tool_name](**arguments)

            # Propagate failures returned by tools.
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
            result = self.execute_step(
                step,
                previous_results=results,
            )

            # Retry a failed step once.
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