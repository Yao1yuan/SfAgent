import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from src.graph import app_graph, AgentState

# Mock the tools to avoid actual execution during graph tests (though we could use real tools if safe)
# But here we focus on routing logic.

def test_graph_initialization():
    """Test that the graph compiles successfully"""
    assert app_graph is not None

@patch("src.graph.get_llm")
def test_coder_generates_tool_call(mock_get_llm):
    """Test Coder node generating a tool call"""
    # Mock LLM response for Coder
    mock_llm = MagicMock()
    mock_response = AIMessage(content="", tool_calls=[
        {"name": "list_directory", "args": {"path": "."}, "id": "call_1"}
    ])
    # IMPORTANT: coder_node calls llm.bind_tools(...).invoke(...)
    # So we must mock the return value of bind_tools().invoke()
    mock_llm.bind_tools.return_value.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    # We can't easily run the graph node-by-node without using the compiled app
    # app_graph.invoke() runs the whole flow.
    # To test individual nodes, we can import them.
    from src.graph import coder_node

    state = {"messages": [HumanMessage(content="List files")], "sender": "user"}
    result = coder_node(state)

    assert result["sender"] == "coder"
    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_calls[0]["name"] == "list_directory"

@patch("src.graph.get_llm")
def test_reviewer_approves(mock_get_llm):
    """Test Reviewer approving a tool call"""
    # Mock LLM response for Reviewer
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="APPROVE")
    mock_get_llm.return_value = mock_llm

    from src.graph import reviewer_node

    # State with a pending tool call
    tool_call_msg = AIMessage(content="", tool_calls=[
        {"name": "list_directory", "args": {"path": "."}, "id": "call_1"}
    ])
    state = {"messages": [tool_call_msg], "sender": "coder"}

    result = reviewer_node(state)

    # Reviewer approves -> sends no new message, just updates sender
    assert result["sender"] == "reviewer"
    assert "messages" not in result # No rejection message added

@patch("src.graph.get_llm")
def test_reviewer_rejects(mock_get_llm):
    """Test Reviewer rejecting a tool call"""
    # Mock LLM response for Reviewer
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="REJECT: Unsafe command")
    mock_get_llm.return_value = mock_llm

    from src.graph import reviewer_node

    # State with a pending tool call
    tool_call_msg = AIMessage(content="", tool_calls=[
        {"name": "run_shell_command", "args": {"command": "rm -rf /"}, "id": "call_1"}
    ])
    state = {"messages": [tool_call_msg], "sender": "coder"}

    result = reviewer_node(state)

    # Reviewer rejects -> adds rejection message
    assert result["sender"] == "reviewer"
    assert len(result["messages"]) == 1
    assert "Compliance Check Failed" in result["messages"][0].content
