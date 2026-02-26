# Project Memory

This file serves as a persistent memory for the project. Important decisions, context, and learnings will be stored here.


## Development Roadmap

### Phase 1: Foundation & Connectivity
- [x] **Step 1: Project Scaffolding**
    - Initialize Python project structure (`src/`, `tests/`, `pyproject.toml`)
    - Create `.env.template`
    - Implement `src/config.py`
- [x] **Step 2: Azure LLM Integration**
    - Create `src/llm.py`
    - Initialize `AzureChatOpenAI`
    - Create `schaeffler-cli ping` command

### Phase 2: Core Tooling & Sandbox
- [x] **Step 3: Secure Local Tools**
    - Create `src/tools/filesystem.py` and `src/tools/terminal.py`
    - Implement `list_directory`, `read_file`, `run_shell_command`
- [x] **Step 4: Advanced Editing**
    - Implement `apply_diff_patch` tool

### Phase 3: The "Brain" (LangGraph Architecture)
- [x] **Step 5: Multi-Agent Workflow**
    - Create `src/graph.py` with `StateGraph`
    - Implement Coder and Compliance Reviewer agents
    - Implement Router and Workflow
- [x] **Step 6: Human-in-the-Loop**
    - Configure `interrupt_before` in `src/graph.py`

### Phase 4: Advanced Engineering
- [x] **Step 7: AST-Based Code Understanding**
    - Integrate `tree-sitter`
    - Create `analyze_code_structure` tool

### Phase 5: User Experience & Integration
- [x] **Step 8: The Interactive UI**
    - Update `src/main.py` with `Rich` Console REPL
    - Implement streaming thoughts and diff rendering
- [x] **Step 9: MCP Integration**
    - Create `src/mcp_loader.py`
    - Implement dynamic MCP loading

