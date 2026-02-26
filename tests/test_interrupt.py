import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from src.graph import app_graph

# Mock get_llm to avoid actual API calls
@patch("src.graph.get_llm")
def test_interrupt_before_tools(mock_get_llm):
    """Test that the graph pauses before executing tools"""

    # 1. Mock Coder response (propose tool call)
    coder_response = AIMessage(content="", tool_calls=[
        {"name": "list_directory", "args": {"path": "."}, "id": "call_1"}
    ])

    # 2. Mock Reviewer response (approve)
    reviewer_response = AIMessage(content="APPROVE")

    # Set up the mock to return these responses in sequence
    # Note: app_graph.invoke calls nodes. Each node calls get_llm().invoke().
    # We need to ensure bind_tools logic works too.

    mock_llm = MagicMock()

    # Coder logic: llm.bind_tools(...).invoke(...)
    mock_llm.bind_tools.return_value.invoke.return_value = coder_response

    # Reviewer logic: llm.invoke(...)
    # We need to make sure the SECOND call (reviewer) returns reviewer_response.
    # But wait, `mock_llm` is reused.
    # `coder_llm.invoke` handles the first call.
    # `llm.invoke` handles the second.

    # We can use side_effect on invoke to return different values.
    # But `coder_llm` is a DIFFERENT mock object returned by `bind_tools`.

    # Mocking strategy:
    # mock_get_llm returns `mock_llm`.
    # `mock_llm.bind_tools.return_value` is `mock_coder_llm`.
    # `mock_coder_llm.invoke` returns `coder_response`.
    # `mock_llm.invoke` (called by reviewer) returns `reviewer_response`.

    mock_coder_llm = MagicMock()
    mock_coder_llm.invoke.return_value = coder_response
    mock_llm.bind_tools.return_value = mock_coder_llm
    mock_llm.invoke.return_value = reviewer_response

    mock_get_llm.return_value = mock_llm

    # Run the graph
    # We must provide a thread_id for persistence
    config = {"configurable": {"thread_id": "test_thread_1"}}
    input_state = {"messages": [HumanMessage(content="List files")], "sender": "user"}

    # Run until interrupt
    # invoke() will run until it hits an interrupt or end.
    # Since we set interrupt_before=["tools"], it should stop there.
    result = app_graph.invoke(input_state, config=config)

    # Check state after interruption
    # get_state(config) returns the current state snapshot
    snapshot = app_graph.get_state(config)

    # Verify we are at the 'tools' node (next)
    assert snapshot.next == ("tools",)

    # Verify the last message in state is the tool call (and sender is reviewer updated)
    # Reviewer returns {"sender": "reviewer"}, so messages list isn't changed by reviewer.
    # So last message is Coder's AIMessage.
    assert isinstance(snapshot.values["messages"][-1], AIMessage)
    assert snapshot.values["messages"][-1].tool_calls[0]["name"] == "list_directory"
