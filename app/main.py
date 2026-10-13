import streamlit as st

from agent.runner import TaskPilotAgent


st.set_page_config(
    page_title="TaskPilot-AI",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 TaskPilot-AI")
st.caption(
    "An autonomous AI agent that plans, executes, "
    "and verifies tasks using local tools."
)

with st.sidebar:
    st.header("System")
    st.write("**LLM:** Qwen through LM Studio")
    st.write("**Execution:** Local document tools")
    st.write("**Verification:** Execution + semantic checks")

    st.info(
        "The current prototype can search and read supported "
        "documents inside data/documents."
    )

st.subheader("Give your agent a task")

user_request = st.text_area(
    "What should TaskPilot do?",
    value="Find the invoice document for ABC Company and read its contents.",
    height=100,
    placeholder="Describe the task you want the agent to complete...",
)

run_clicked = st.button(
    "▶ Run Agent",
    type="primary",
    use_container_width=True,
)

if run_clicked:
    if not user_request.strip():
        st.warning("Please enter a task.")
    else:
        try:
            with st.spinner(
                "Planning, executing, and verifying your task..."
            ):
                agent = TaskPilotAgent()
                output = agent.run(user_request)

            st.subheader("1. Generated Plan")
            st.json(output["plan"])

            st.subheader("2. Execution Results")

            for index, result in enumerate(
                output["results"],
                start=1,
            ):
                with st.expander(
                    f"Step {index}: {result.get('tool', 'Unknown tool')}",
                    expanded=True,
                ):
                    if result.get("success"):
                        st.success("Tool executed successfully")
                        st.json(result.get("result"))
                    else:
                        st.error(
                            result.get("error", "Execution failed")
                        )

                    if result.get("retry_attempted"):
                        st.caption("A retry was attempted.")

            st.subheader("3. Verification")

            verification = output["verification"]

            if verification["verified"]:
                st.success("✅ Task completed and verification passed.")
            else:
                st.error("❌ Task could not be fully verified.")

            st.json(verification)

        except Exception as exc:
            st.error(
                "The agent encountered an error and could not "
                "complete the request."
            )
            st.exception(exc)