

# 📋 Schaeffler Code CLI - Enterprise Architecture Guide

## 🏢 1. Project Context & Security Mandate
**Objective**: Build a secure, autonomous, enterprise-grade AI Developer CLI for **Schaeffler**. This tool mimics the capabilities of "Claude Code" but runs entirely within Schaeffler's secure infrastructure using Azure OpenAI.

**🚨 Critical Compliance Rules (Zero Tolerance):**
1.  **Zero Telemetry**: ABSOLUTELY NO analytics, tracking, or external data logging code allowed.
2.  **Azure OpenAI Only**: Must use `AzureChatOpenAI` endpoints. No public API calls.
3.  **Human-in-the-Loop (HITL)**: Any file modification or shell execution MUST be intercepted and require explicit human `[Y/n]` approval.
4.  **Multi-Agent Safety**: All code changes must pass an automated "Compliance Reviewer Agent" check before reaching the human approval stage.

## 🛠️ 2. Tech Stack
-   **Language**: Python 3.10+
-   **Core Framework**: `LangGraph` (State management & Orchestration).
-   **LLM Interface**: `LangChain-OpenAI` (specifically `AzureChatOpenAI`).
-   **CLI/UI**: `Typer` (CLI routing) + `Rich` (Markdown rendering & interactive prompts).
-   **Advanced Analysis**: `tree-sitter` (AST-based code understanding).
-   **External Integration**: `mcp` (Model Context Protocol SDK).

---

## 🚀 3. Development Roadmap (Execute Step-by-Step)

**Instruction to Claude Code**: Read the entire guide first. Then, execute **one step at a time**. After finishing a step, create a Git commit with a descriptive message, and pause to ask for user confirmation before proceeding.

### Phase 1: Foundation & Connectivity

#### Step 1: Project Scaffolding
-   Initialize a Python project structure (`src/`, `tests/`, `pyproject.toml`).
-   Create a `.env.template` listing required variables: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`.
-   Implement `src/config.py` to load environment variables securely using `pydantic-settings`.

#### Step 2: Azure LLM Integration
-   Create `src/llm.py`.
-   Initialize `AzureChatOpenAI` with temperature=0 (for coding precision).
-   Create a simple CLI command `schaeffler-cli ping` that sends a "Hello World" prompt to Azure and prints the response to verify connectivity.

### Phase 2: Core Tooling & Sandbox

#### Step 3: Secure Local Tools (The "Hands")
-   Create `src/tools/filesystem.py` and `src/tools/terminal.py`.
-   Implement LangChain `@tool` functions:
    -   `list_directory(path)`: Lists files (respect `.gitignore`).
    -   `read_file(path)`: Reads file content.
    -   `run_shell_command(command)`: **Security Requirement**: Use `subprocess.run`. Restrict the working directory to the project root. Do NOT allow commands like `rm -rf /` or access to system paths (`/etc`, `~/.ssh`).

#### Step 4: Advanced Editing - Search/Replace (Best Practice)
-   *Constraint*: Do not rewrite entire files (wasteful & error-prone).
-   Implement a `apply_diff_patch(filepath, search_block, replace_block)` tool.
-   The LLM must locate the `search_block` in the file and replace it with `replace_block`. Raise an error if the block is not found (prevents hallucinations).

### Phase 3: The "Brain" (LangGraph Architecture)

#### Step 5: Multi-Agent Workflow (The "ReAct" Loop)
-   Create `src/graph.py`. Define a `StateGraph`.
-   **Agent 1: Coder**: The worker who proposes changes.
-   **Agent 2: Compliance Reviewer**: A separate LLM call (system prompt: "Check for hardcoded secrets, PII, and destructive commands").
-   **Workflow**:
    1.  User Input -> **Coder**.
    2.  Coder proposes a Tool Call (e.g., `apply_diff_patch`).
    3.  **Router**: Route to **Reviewer** before executing.
    4.  Reviewer analyzes the diff.
        -   If *Reject*: Send feedback back to **Coder** to fix.
        -   If *Approve*: Proceed to **Human Approval**.

#### Step 6: Human-in-the-Loop (The "Kill Switch")
-   In `src/graph.py`, configure `interrupt_before=["tools"]` (or the specific node that executes tools).
-   This ensures the graph **freezes** execution right after the Reviewer approves but *before* the file is actually touched.

### Phase 4: Advanced Engineering (Inspired by Industry Standards)

#### Step 7: AST-Based Code Understanding (Tree-sitter)
-   Integrate the `tree-sitter` library.
-   Create a tool `analyze_code_structure(filepath)`.
-   Instead of reading raw text, this tool returns a **skeletal outline** (classes, methods, signatures) of the file.
-   *Benefit*: Allows the Agent to understand massive files without consuming context window limits.

### Phase 5: User Experience & Integration

#### Step 8: The Interactive UI (Rich)
-   Update `src/main.py`.
-   Build a REPL (Read-Eval-Print Loop) using `Rich` Console.
-   Stream the LLM's thought process (e.g., `[Coder] Thinking...`, `[Reviewer] Checking security...`) in real-time.
-   **Crucial**: When the LangGraph interrupts for Human Approval, render a clear, warning-colored Diff of the proposed changes and ask: `⚠️ Approve changes to 'main.py'? [y/N]`.

#### Step 9: MCP Integration (Future-Proofing)
-   Create `src/mcp_loader.py` using `langchain-mcp-adapters`.
-   Allow the CLI to read a `schaeffler_mcp_config.json` file to dynamically load internal MCP servers (e.g., Jira, GitLab).
-   Inject these external tools into the Coder Agent's capability list at runtime.

---

**Message to Claude Code**:
I have provided the `schaeffler_agent_build.md` file above. Please acknowledge receipt and understanding of the **Security Mandates**. Then, begin with **Phase 1, Step 1**.