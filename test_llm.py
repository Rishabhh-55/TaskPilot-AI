from agent.planner import Planner
from agent.executor import Executor
from agent.verifier import Verifier

from tools.files import search_files, read_file


def main():
    available_tools = [
        {
            "name": "search_files",
            "description": "Search document filenames.",
            "arguments": {
                "query": "string",
            },
        },
        {
            "name": "read_file",
            "description": "Read a supported text document.",
            "arguments": {
                "path": "string",
            },
        },
    ]

    registered_tools = {
        "search_files": search_files,
        "read_file": read_file,
    }

    request = (
        "Find the invoice document for ABC Company "
        "and read its contents."
    )

    print("1. Creating plan...", flush=True)

    planner = Planner()
    plan = planner.create_plan(
        user_request=request,
        available_tools=available_tools,
    )

    print("\nGenerated plan:")
    print(plan)

    print("\n2. Executing plan...", flush=True)

    executor = Executor(registered_tools)
    results = executor.execute_plan(plan)

    for index, result in enumerate(results, start=1):
        print(f"\nStep {index} result:")
        print(result)

    print("\n3. Verifying execution...", flush=True)

    verifier = Verifier()
    verification = verifier.verify_execution(plan, results)

    print("\nVerification:")
    print(verification)


if __name__ == "__main__":
    main()