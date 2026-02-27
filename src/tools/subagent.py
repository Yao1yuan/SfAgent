from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any, Optional

# Import read-only tools
from src.tools.filesystem import list_directory, read_file
from src.tools.terminal import run_shell_command
from src.llm import get_llm

# Define the set of tools available to the sub-agent (READ-ONLY)
SUBAGENT_TOOLS = [list_directory, read_file, run_shell_command]

@tool
def delegate_research(task_description: str) -> str:
    """
    Delegate a research task to a temporary sub-agent.
    Use this for reading multiple files, exploring directories, or investigating code
    without polluting your main context window.

    The sub-agent has access to read-only tools (list_directory, read_file, run_shell_command).
    It does NOT have access to write_file or apply_diff_patch.

    Args:
        task_description: The specific research question or task for the sub-agent.

    Returns:
        A summary of the findings found by the sub-agent.
    """
    print(f"\n[Sub-Agent] Starting research task: {task_description}")

    # 1. Initialize fresh LLM and bind tools
    llm = get_llm()
    llm_with_tools = llm.bind_tools(SUBAGENT_TOOLS)

    # 2. Initialize fresh message history
    messages = [
        SystemMessage(content=(
            "You are a ephemeral Research Sub-Agent. "
            "Your goal is to investigate the codebase and answer the user's question. "
            "You have access to READ-ONLY tools. "
            "You cannot modify files. "
            "Perform the necessary research (list files, read content) and then provide a final summary answer. "
            "Do not ask the user for more input. "
            "When you have the answer, respond with the final summary directly."
        )),
        HumanMessage(content=task_description)
    ]

    # 3. Run the ReAct loop (simple manual loop for isolation)
    max_turns = 10
    final_answer = ""

    tool_map = {t.name: t for t in SUBAGENT_TOOLS}

    for turn in range(max_turns):
        # Invoke LLM
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # Check if it's a tool call or final answer
        if response.tool_calls:
            print(f"[Sub-Agent] Turn {turn+1}: Calling tools {[tc['name'] for tc in response.tool_calls]}...")

            # Execute tools
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_id = tc["id"]

                if tool_name in tool_map:
                    try:
                        tool_result = tool_map[tool_name].invoke(tool_args)
                    except Exception as e:
                        tool_result = f"Error: {str(e)}"
                else:
                    tool_result = f"Error: Tool {tool_name} not found or not allowed."

                # Append tool result
                messages.append(ToolMessage(
                    tool_call_id=tool_id,
                    content=str(tool_result),
                    name=tool_name
                ))
        else:
            # No tool calls -> Final Answer
            final_answer = response.content
            print(f"[Sub-Agent] Finished. Returning summary.")
            break

    if not final_answer and turn == max_turns - 1:
        final_answer = "Sub-agent reached maximum turn limit without a final answer. Partial findings may be in the logs (discarded)."

    return f"Research Findings:\n{final_answer}"
