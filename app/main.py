import streamlit as st

from agent.runner import TaskPilotAgent


st.set_page_config(
    page_title="TaskPilot-AI",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 TaskPilot-AI")
st.caption(
    "An AI agent that plans, executes, and verifies tasks "
    "using local tools and a human approval checkpoint."
)

with st.sidebar:
    st.header("System")
    st.write("**LLM:** Qwen through LM Studio")
    st.write("**Execution:** Local document tools and SQLite")
    st.write("**Verification:** Execution and semantic checks")

    st.info(
        "The agent generates a plan first. Nothing executes until "
        "you review the plan and explicitly approve it."
    )

st.subheader("Give your agent a task")

user_request = st.text_area(
    "What should TaskPilot do?",
    value=(
        "Find the invoice document for ABC Company "
        "and read its contents."
    ),
    height=100,
    placeholder="Describe the task you want the agent to complete...",
)

if "pending_plan" not in st.session_state:
    st.session_state.pending_plan = None

if "pending_request" not in st.session_state:
    st.session_state.pending_request = None

if "execution_output" not in st.session_state:
    st.session_state.execution_output = None


def clear_pending():
    st.session_state.pending_plan = None
    st.session_state.pending_request = None
    st.session_state.execution_output = None


col1, col2 = st.columns(2)

with col1:
    plan_clicked = st.button(
        "1. Generate Plan",
        type="primary",
        use_container_width=True,
    )

with col2:
    cancel_clicked = st.button(
        "Cancel / Reset",
        use_container_width=True,
    )

if cancel_clicked:
    clear_pending()
    st.rerun()

if plan_clicked:
    if not user_request.strip():
        st.warning("Please enter a task.")
    else:
        try:
            with st.spinner("Generating a plan..."):
                agent = TaskPilotAgent()
                planned = agent.plan(user_request)

            st.session_state.pending_plan = planned["plan"]
            st.session_state.pending_request = user_request
            st.session_state.execution_output = None

        except Exception as exc:
            st.error(f"Planning failed: {exc}")


if st.session_state.pending_plan is not None:
    st.divider()
    st.subheader("1. Review the generated plan")

    st.write("**Goal:**", st.session_state.pending_plan.get("goal"))
    st.json(st.session_state.pending_plan)

    st.warning(
        "Review the proposed tools and arguments carefully. "
        "Approving this plan authorizes its steps to execute."
    )

    approved = st.checkbox(
        "I have reviewed this plan and approve its execution.",
        key="approval_checkbox",
    )

    if st.button(
        "2. Approve & Execute",
        type="primary",
        disabled=not approved,
        use_container_width=True,
    ):
        try:
            with st.spinner("Executing approved plan and verifying results..."):
                agent = TaskPilotAgent()
                output = agent.execute_approved_plan(
                    st.session_state.pending_plan
                )

            st.session_state.execution_output = output
            st.session_state.pending_plan = None
            st.session_state.pending_request = None

        except Exception as exc:
            st.error(f"Execution failed: {exc}")


if st.session_state.execution_output is not None:
    output = st.session_state.execution_output

    st.divider()
    st.subheader("2. Execution Results")

    for index, result in enumerate(output["results"], start=1):
        tool_name = result.get("tool", "Unknown tool")

        with st.expander(
            f"Step {index}: {tool_name}",
            expanded=True,
        ):
            if result.get("success"):
                st.success("Tool executed successfully")
                st.json(result.get("result"))
            else:
                st.error(result.get("error", "Execution failed"))

            if result.get("retry_attempted"):
                st.caption("A retry was attempted.")

    st.subheader("3. Verification")

    verification = output["verification"]

    if verification.get("verified"):
        st.success("✅ Task completed and verification passed.")
    else:
        st.error("❌ Verification did not pass.")

    st.json(verification)

    if st.button("Start a New Task"):
        clear_pending()
        st.rerun()