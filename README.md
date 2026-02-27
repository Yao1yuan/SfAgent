
# SF Code CLI 


**Secure. Compliant. Autonomous.**

**SF Code CLI** is an enterprise-grade, interactive AI developer agent designed to run securely within the SF corporate environment. It acts as an internal, compliant alternative to tools like Claude Code CLI or GitHub Copilot Workspace, providing developers with a powerful, context-aware coding assistant that understands your entire codebase.

This tool is built from the ground up with a focus on **security**, **data privacy**, and **developer productivity**.

---

## ✨ Core Features

*   **🤖 Advanced Agentic Workflow**: Powered by LangGraph, the agent can plan, execute multi-step tasks, and self-correct based on tool outputs.
*   **🛡️ Enterprise-Grade Security**:
    *   **Human-in-the-Loop (HITL)**: No file modifications or shell commands are executed without explicit `[y/n/always]` user approval.
    *   **Zero Telemetry**: No usage data, code, or metadata is ever sent to third-party servers. All interactions are strictly between your local machine and SF's private Azure OpenAI instance.
*   **🧠 Intelligent Code Understanding**:
    *   **AST Analysis**: Uses `tree-sitter` to parse code into abstract syntax trees, enabling deep semantic understanding beyond simple text matching.
    *   **Sub-Agent Delegation**: Spawns ephemeral, read-only sub-agents for research tasks (`/delegate_research`), keeping the main context window clean and focused.
*   **♾️ Infinite Context & Memory**:
    *   **Context Compression**: Automatically summarizes old parts of the conversation to prevent token limit errors in long sessions.
    *   **Persistent Task Management**: Manages complex project plans in a local `.json` file, allowing work to be resumed across sessions.
*   **🔌 Extensible & Customizable**:
    *   **Slash Commands**: Intuitive commands like `/skills`, `/load`, and `/auto` for a fast, mouse-free workflow.
    *   **Skill Injection**: Dynamically load SF-specific domain knowledge (e.g., coding standards, testing procedures) from a local `.schaeffler/skills/` directory.
    *   **MCP Integration**: Ready to connect with internal Model Context Protocol (MCP) servers for seamless access to tools like Jira, GitLab, and internal databases.
*   **🚀 Modern CLI Experience**:
    *   **Auto-Completion**: Interactive `prompt_toolkit` interface with real-time command suggestions and descriptions.
    *   **Expandable Outputs**: Long outputs from tools or the agent's thoughts can be expanded (`v` or `t`) or kept collapsed for a clean UI.
    -   **Graceful Interruption**: Stop the agent's generation at any time with `Ctrl+C` without crashing the application.

---

## 🛠️ Getting Started

### Prerequisites

*   Python 3.10+
*   Access to SF's internal Azure OpenAI endpoint.
*   Required environment variables (see below).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd SF-Code-CLI
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root by copying `.env.template`. Fill in your credentials for SF's Azure OpenAI service:
    ```ini
    # .env
    AZURE_OPENAI_API_KEY="your_secret_key"
    AZURE_OPENAI_ENDPOINT="https://schaeffler-internal.openai.azure.com/"
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"
    AZURE_OPENAI_API_VERSION="2024-02-15-preview"
    ```

### Running the CLI

Start the interactive chat session with:

```bash
python src/main.py chat
```

Once inside, type `/help` to see a list of available slash commands.

---

## 💻 Usage & Workflow

### Basic Interaction

Simply describe your coding task in natural language. The agent will formulate a plan, propose tool calls, and ask for your approval before making any changes.

**Example:**
> You: Refactor `src/utils.py` to use dependency injection. Start by creating a task plan.

### Using Slash Commands

Slash commands provide quick access to powerful features without consuming LLM context.

*   `/skills`: See what internal knowledge documents (e.g., `git_workflow.md`) are available.
*   `/load <skill_name>`: Inject a specific skill into the agent's memory for the current task.
*   `/auto`: Toggle "Always Approve" mode for rapid, uninterrupted refactoring.
*   `/exit`: Quit the application.

### The Approval Prompt

When the agent needs to modify your system, you'll see a prompt:

```
⚠️  Pending Tool Execution (Paused for Approval):
  apply_diff_patch: {'filepath': 'src/main.py', ...}
Approve execution? [y/n/always]
```
-   `y`: Approve this single action.
-   `n`: Reject this single action. The agent will be notified and will try to find another way.
-   `always`: Approve this and all subsequent actions in this session (activates `/auto` mode).

---

## 🏗️ Architecture Overview

The agent is built on a robust, stateful architecture using **LangGraph**. The core loop follows a secure `Coder -> Human Approval -> Tool Execution` flow. Features like Sub-Agents and Context Compression are implemented as tools or middleware within this graph, ensuring a modular and maintainable codebase.

---

## 🤝 Contributing

This is an internal SF project. Please refer to the internal contribution guidelines or contact the project maintainers for details on how to contribute.
```
