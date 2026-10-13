# TaskPilot-AI

**An AI-powered task automation agent that plans, executes, and verifies tasks using natural language instructions.**

TaskPilot-AI uses a local Large Language Model (LLM) to convert user requests into structured execution plans. It executes these plans through Python tools and verifies whether the requested outcomes have been achieved.

## Features

- **AI Task Planning:** Converts natural language instructions into structured, multi-step plans using Qwen.
- **Tool-Based Execution:** Executes planned steps using available Python tools.
- **Invoice Processing:** Searches documents, extracts invoice information, validates fields, and stores records in SQLite.
- **Document Search:** Searches and reads local documents.
- **Invoice Management:** Creates, retrieves, and lists invoice records.
- **Result Verification:** Checks execution results and validates whether the requested conditions are satisfied.
- **Error Handling:** Detects invalid tool arguments and execution failures.
- **Duplicate Detection:** Identifies previously processed invoices to avoid unnecessary duplicate processing.
- **Interactive Dashboard:** Provides a Streamlit interface for submitting tasks and viewing execution results.
- **Automated Testing:** Includes tests for invoice processing, planning validation, and verification.

## Architecture

TaskPilot-AI follows a **Plan → Execute → Verify** workflow.

1. **Planning:** The Planner uses Qwen to convert the user's request into a structured plan.
2. **Execution:** The Executor validates the planned steps and invokes the appropriate tools.
3. **Tool Operations:** Python tools perform document operations and interact with the SQLite invoice database.
4. **Verification:** The Verifier checks execution results and evaluates whether the requested conditions have been met.
5. **Output:** The application presents the execution results and verification status.

## Technology Stack

- **Language:** Python
- **LLM:** Qwen 3.5 9B
- **Local Model Runtime:** LM Studio
- **User Interface:** Streamlit
- **Database:** SQLite
- **Testing:** Python `unittest`

## Project Structure

```text
TaskPilot-AI/
├── agent/
│   ├── executor.py
│   ├── invoice_processor.py
│   ├── llm_client.py
│   ├── memory.py
│   ├── planner.py
│   ├── runner.py
│   ├── verifier.py
│   └── workflow.py
├── app/
│   └── main.py
├── data/
│   └── documents/
├── tests/
│   ├── test_invoices.py
│   ├── test_invoices_workflow.py
│   └── test_planner.py
├── tools/
│   ├── files.py
│   └── invoices.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup and Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd TaskPilot-AI
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure LM Studio

1. Install and open LM Studio.
2. Download and load the Qwen model used by the project.
3. Start the local API server.
4. Ensure the server is available at `http://127.0.0.1:1234`.

The application uses an OpenAI-compatible API endpoint to communicate with the local model.

Ensure that the model configuration in `agent/llm_client.py` matches your LM Studio setup.

## Run the Application

From the project root, execute:

```powershell
python -m streamlit run app/main.py
```

Open the local URL displayed in the terminal, usually:

`http://localhost:8501`

Enter a task in the dashboard and click **Run Agent** to execute it.

## Example Tasks

**Process an invoice:**

```text
Process the invoice for XYZ Corporation.
```

**Process an invoice and verify the database:**

```text
Process the invoice for ABC Company, list all invoices, and verify that ABC Company appears in the database.
```

The agent generates a plan, executes the required tools, and returns the results along with verification information.

## Run Tests

Execute the automated test suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests cover document operations, invoice workflows, planning validation, and verification behavior.

## Data Storage

Invoice records are stored in a local SQLite database. Sample invoice documents are maintained in `data/documents/`.

The database is generated locally by the application and should not be committed unless explicitly required.

## Limitations

- The local LLM must be available through the configured LM Studio API.
- Supported operations depend on the tools implemented in the project.
- Extraction and verification accuracy depend on document contents and the implemented validation rules.

## Future Improvements

- Support additional document formats and automation tools.
- Improve recovery from failed execution steps.
- Expand automated testing and evaluation.
- Add execution logging and more configurable verification criteria.