from typing import TypedDict, Annotated, List, Literal, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator

from src.llm import get_llm
from src.tools.filesystem import list_directory, read_file
from src.tools.terminal import run_shell_command
from src.tools.editor import apply_diff_patch
from src.tools.analysis import analyze_code_structure
from src.tools.subagent import delegate_research
from src.mcp_loader import MCPManager
from src.compression import compress_history
from src.task_manager import task_create, task_complete, task_list
from src.tools.skills import list_available_skills, load_skill

# Core Tools
CORE_TOOLS = [
    list_directory, read_file, run_shell_command, apply_diff_patch,
    analyze_code_structure, delegate_research,
    task_create, task_complete, task_list,
    list_available_skills, load_skill
]

def get_all_tools():
    """Return all tools including dynamically loaded MCP tools"""
    return CORE_TOOLS + MCPManager.get_tools()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    sender: str

# --- Nodes ---

async def coder_node(state: AgentState):
    """Main Coder Agent"""
    print("🤖 [Coder] Thinking...")

    # 1. Compress History (Prevent Token Overflow)
    # We pass the compressed view to the LLM, but we don't destructively modify
    # the state here (to keep history for the user), unless auto-compact triggers.
    compressed_messages = compress_history(state["messages"])

    llm = get_llm()
    current_tools = get_all_tools()
    coder_llm = llm.bind_tools(current_tools)

    # System Prompt with explicit "Laziness" instruction
    system_message = (
        "You are an expert Senior Python Developer at Schaeffler. "
        "Your goal is to complete tasks securely and efficiently.\n"
        "Security Rules:\n"
        "1. No telemetry. No external API calls (except Azure).\n"
        "2. No hardcoded secrets.\n"
        "3. Always use `task_create` to plan before complex coding.\n"
        "Behavior Rules:\n"
        "- Do NOT list directories or read files proactively unless asked.\n"
        "- If the user says 'Hello', just reply 'Hello'.\n"
        "- Use `delegate_research` for large-scale information gathering.\n"
        "Domain Knowledge:\n"
        "- You can use `list_available_skills` to see available Schaeffler internal guidelines.\n"
        "- Use `load_skill` to read a specific guideline when the user asks you to follow a certain process.\n"
        "ERROR HANDLING:\n"
        "- You MUST read the exact output of your tool calls. If a tool returns a string starting with 'Error:', "
        "you MUST NOT pretend it succeeded. You must inform the user about the error and try to fix it or stop.\n"
    )

    # Prepend System Message
    messages_for_llm = [HumanMessage(content=system_message)] + compressed_messages

    response = await coder_llm.ainvoke(messages_for_llm)
    return {"messages": [response], "sender": "coder"}

async def tool_execution_node(state: AgentState):
    """Dynamic Tool Executor"""
    print("🛠️ [Tools] Executing...")

    messages = state["messages"]
    last_message = messages[-1]

    # Get tools map
    tool_map = {t.name: t for t in get_all_tools()}
    results = []

    for tool_call in last_message.tool_calls:
        try:
            tool = tool_map.get(tool_call["name"])
            if tool:
                # Execute
                output = await tool.ainvoke(tool_call["args"])
            else:
                output = f"Error: Tool {tool_call['name']} not found."
        except Exception as e:
            output = f"Tool Execution Error: {str(e)}"

        results.append(ToolMessage(
            tool_call_id=tool_call["id"],
            content=str(output),
            name=tool_call["name"]
        ))

    return {"messages": results, "sender": "tools"}

# --- Routers ---

def router_coder(state: AgentState):
    msg = state["messages"][-1]
    if msg.tool_calls:
        return "tools"
    return "__end__"

# --- Graph ---

def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("coder", coder_node)
    workflow.add_node("tools", tool_execution_node)

    workflow.set_entry_point("coder")

    workflow.add_conditional_edges("coder", router_coder, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "coder")

    # Persistence
    memory = MemorySaver()

    # ⚠️ CRITICAL: The interrupt happens BEFORE the 'tools' node runs.
    # This gives the Human user a chance to see the plan and still say NO.
    return workflow.compile(checkpointer=memory, interrupt_before=["tools"])

app_graph = create_graph()
