from typing import TypedDict, Annotated, List, Literal, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
# Removed unused pydantic import
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import operator

from src.llm import get_llm
from src.tools.filesystem import list_directory, read_file
from src.tools.terminal import run_shell_command
from src.tools.editor import apply_diff_patch
from src.tools.analysis import analyze_code_structure
from src.mcp_loader import load_mcp_tools

# Define Tools
# We load core tools + MCP tools
TOOLS = [list_directory, read_file, run_shell_command, apply_diff_patch, analyze_code_structure]
MCP_TOOLS = load_mcp_tools()
TOOLS.extend(MCP_TOOLS)

# Define State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    sender: str

# --- Nodes ---

def coder_node(state: AgentState):
    """
    The Coder agent responsible for generating code and tool calls.
    """
    llm = get_llm()
    # Bind tools to the LLM
    coder_llm = llm.bind_tools(TOOLS)

    system_message = (
        "You are an expert Senior Python Developer at Schaeffler. "
        "Your goal is to complete the user's task securely and efficiently.\n"
        "You have access to filesystem and terminal tools. "
        "ALWAYS use the provided tools to modify files or run commands. "
        "Do NOT hallucinate file contents.\n"
        "Compliance: No telemetry, no hardcoded secrets, no destructive commands."
    )

    messages = [HumanMessage(content=system_message)] + state["messages"]
    response = coder_llm.invoke(messages)

    return {"messages": [response], "sender": "coder"}

def reviewer_node(state: AgentState):
    """
    The Compliance Reviewer agent. Checks the Coder's proposed tool calls.
    """
    last_message = state["messages"][-1]

    # If no tool calls, nothing to review (or maybe review the text response?)
    # For now, we focus on tool calls interception.
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        # If Coder didn't call a tool, we might want to just pass it through or
        # checking if it's a final answer.
        # But per requirements: "Reviewer analyzes the diff."
        # If it's just text, we assume it's safe or irrelevant for the reviewer?
        # Let's say we approve text-only responses automatically for now.
        return {"messages": [AIMessage(content="APPROVE_TEXT")], "sender": "reviewer"}

    tool_calls = last_message.tool_calls

    llm = get_llm()

    # Create a prompt for the reviewer
    # We serialize the tool calls to text for the reviewer to analyze
    tool_calls_text = str(tool_calls)

    system_message = (
        "You are a Compliance Reviewer at Schaeffler. "
        "Your job is to analyze the proposed tool execution for security risks.\n"
        "Rules:\n"
        "1. No hardcoded secrets (API keys, passwords).\n"
        "2. No PII (Personal Identifiable Information).\n"
        "3. No destructive commands (rm -rf, etc.).\n"
        "4. No telemetry or external data logging.\n"
        "\n"
        "Analyze the following tool calls:\n"
        f"{tool_calls_text}\n"
        "\n"
        "Response Format:\n"
        "If safe: Respond with exactly 'APPROVE'.\n"
        "If unsafe: Respond with 'REJECT: <reason>'."
    )

    response = llm.invoke([HumanMessage(content=system_message)])
    content = response.content.strip()

    # We don't add the reviewer's internal thought process to the main history
    # to avoid confusing the Coder, unless it's a rejection.
    # Actually, we should probably output a special message indicating status.

    if "APPROVE" in content.upper():
        # Proceed to tools
        return {"sender": "reviewer"} # No new message added to history, just signal
    else:
        # Reject: Add a tool message simulating a failure or just a HumanMessage
        # telling the Coder to fix it.
        # Ideally we should construct a ToolMessage indicating failure, but
        # since the tool hasn't run, we can just feed back the rejection as a user/system message.
        rejection_msg = HumanMessage(
            content=f"Compliance Check Failed: {content}. Please fix your request."
        )
        return {"messages": [rejection_msg], "sender": "reviewer"}

# --- Tool Node ---
tool_node = ToolNode(TOOLS)

# --- Routing ---

def router(state: AgentState) -> Literal["reviewer", "__end__", "continue"]:
    messages = state["messages"]
    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "reviewer"
    return "__end__" # Or continue conversation?

def reviewer_router(state: AgentState) -> Literal["tools", "coder"]:
    messages = state["messages"]
    last_message = messages[-1]

    # If the last message is from the reviewer (rejection), it's a HumanMessage (simulated).
    # Wait, in reviewer_node, if REJECT, we added a HumanMessage.
    # If APPROVE, we added NOTHING (or a placeholder).

    # Logic:
    # If last message is HumanMessage (Rejection) -> back to Coder.
    # If last message is AIMessage (Coder's original tool call) -> means we approved and didn't add new msg.
    # Wait, if we return {"sender": "reviewer"}, state["messages"] is unchanged?
    # No, state update usually merges.

    sender = state.get("sender", "")

    if sender == "reviewer":
        # If reviewer sent a message, it must be a rejection (HumanMessage)
        # Check content
        if isinstance(last_message, HumanMessage) and "Compliance Check Failed" in last_message.content:
            return "coder"

        # If it was "APPROVE_TEXT" (AIMessage), we end?
        if isinstance(last_message, AIMessage) and "APPROVE_TEXT" in last_message.content:
            return "coder" # Or end? Coder might want to continue.

    # If sender was NOT reviewer (meaning we didn't add messages in approve path),
    # or if we are just checking the state:
    # Actually, if Reviewer approves, we want to go to Tools.
    # But how do we distinguish "Reviewer Approved" vs "Reviewer Rejected" if we didn't add a message?
    # We can use a separate key in state, or check if the last message is still the tool call.

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # It's the original tool call, meaning it wasn't buried by a rejection message.
        return "tools"

    return "coder"

# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("coder", coder_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("coder")

workflow.add_conditional_edges(
    "coder",
    router,
    {
        "reviewer": "reviewer",
        "__end__": END,
        "continue": "coder"
    }
)

workflow.add_conditional_edges(
    "reviewer",
    reviewer_router,
    {
        "tools": "tools",
        "coder": "coder"
    }
)

workflow.add_edge("tools", "coder")

# Initialize memory for persistence
memory = MemorySaver()

# Compile with interrupt and checkpointer
app_graph = workflow.compile(checkpointer=memory, interrupt_before=["tools"])
