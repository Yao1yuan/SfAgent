# 📋 Schaeffler Code CLI - Phase 2: Advanced Architecture Upgrade

**Current Status**: We have built a basic MVP Agent using LangGraph, Azure OpenAI, and local file tools.
**Goal**: Upgrade the system to enterprise standards by implementing **Context Management**, **Task Persistence**, and **Sub-Agent Delegation** (inspired by the "learn-claude-code" curriculum s04/s06/s07).

**Constraint**: Do NOT break existing functionality. Refactor and extend the current `src/` codebase.

---

## 🚀 Upgrade Roadmap (Execute Step-by-Step)

**Instruction to Claude Code**: Read this entire file. Then, execute **one step at a time**. After finishing a step, create a Git commit, and pause for user confirmation.

### Step 1: Implement "Sub-Agent Delegation" (Context Isolation)
**Reference**: s04 (Subagents)
**Objective**: Allow the main agent to spawn ephemeral sub-agents to perform read-only research tasks without polluting the main context window.

1.  **Modify `src/tools.py`**:
    -   Create a new tool function: `delegate_research(task_description: str) -> str`.
    -   **Implementation**:
        -   Inside this function, initialize a **fresh** `AzureChatOpenAI` instance and a **new** list of messages (System Prompt + User Task).
        -   Give this sub-agent access ONLY to read-only tools: `read_file`, `list_directory`, `run_shell_command` (restricted). **Do NOT** give it `write_file` or `delegate_research` (prevent infinite recursion).
        -   **Loop**: Run the sub-agent loop for up to 10 turns or until it answers.
        -   **Return**: The final answer/summary from the sub-agent.
        -   **Discard**: The entire conversation history of the sub-agent is thrown away.
2.  **Update `src/agent.py`**:
    -   Add `delegate_research` to the list of tools available to the main **Coder Agent**.
    -   Update System Prompt: *"You can use `delegate_research` to investigate large codebases or documentation. This saves your own context window."*

### Step 2: Implement "Context Compression" (Infinite Memory)
**Reference**: s06 (Context Compact)
**Objective**: Prevent Azure OpenAI Token Limit errors during long sessions by summarizing old history.

1.  **Create `src/compression.py`**:
    -   Implement a function `compress_history(messages: list) -> list`.
    -   **Logic**:
        -   Identify `ToolMessage` (tool outputs) that are older than 5 turns.
        -   Truncate their content to 100 characters (e.g., `[Output truncated: ...]` or `[File content hidden]`).
        -   Keep the most recent 5 turns fully intact.
2.  **Integrate into `src/agent.py`**:
    -   In the LangGraph loop (before calling the LLM), call `compress_history(state["messages"])`.
    -   **Auto-Summarization**: If the total token count exceeds 20,000 (estimate: 1 char ~= 0.25 tokens), insert a "System Summary" message at the beginning and remove the oldest 10 messages.

### Step 3: Implement "Persistent Task System" (Project Management)
**Reference**: s07 (Task System)
**Objective**: Allow the agent to plan complex refactors and resume work after a crash.

1.  **Create `src/task_manager.py`**:
    -   Define a `Task` class (id, title, status, dependencies).
    -   Implement methods to load/save tasks to `.schaeffler/tasks.json`.
2.  **Add Tools in `src/tools.py`**:
    -   `task_create(title, dependency_ids)`: Create a blocked task.
    -   `task_complete(task_id)`: Mark done and check if dependent tasks can be unblocked.
    -   `task_list()`: Show all tasks, marking which are `[BLOCKED]`, `[PENDING]`, or `[DONE]`.
3.  **Update `src/agent.py`**:
    -   Bind these new tools to the Coder Agent.
    -   Update System Prompt: *"Always create a plan using `task_create` before starting a complex coding task."*

### Step 4: Verify & Test
1.  **Test Sub-Agent**: Ask the CLI: *"Research how `src/config.py` is implemented using a sub-agent, then tell me the summary."* Verify that the main context is not flooded with file reads.
2.  **Test Task System**: Ask: *"Create a plan to refactor `src/main.py`. Step 1: Read file. Step 2: Rename variable."* Verify `.schaeffler/tasks.json` is created.
3.  **Test Compression**: (Simulated) Manually inject a long dummy message into the state and verify it gets truncated in the next turn.

---

**Message to Claude Code**:
I have provided `update_agent.md`. We are upgrading our existing agent. Please start with **Step 1**.