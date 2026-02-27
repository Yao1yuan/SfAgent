import typer
import sys
import uuid
import os
import asyncio
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import app_graph
from src.llm import get_llm
from src.mcp_loader import MCPManager
from src.tools.skills import get_all_skills, read_skill_content

app = typer.Typer(no_args_is_help=True)
console = Console()

@app.callback()
def main():
    """
    Schaeffler CLI - Secure AI Developer Agent
    """
    pass

@app.command()
def chat():
    """
    Start an interactive chat session with the AI Agent.
    """
    asyncio.run(run_chat_loop())

async def run_chat_loop():
    console.print(Panel.fit("[bold blue]Schaeffler AI Developer CLI[/bold blue]\n[dim]Secure. Compliant. Autonomous.[/dim]", border_style="blue"))
    console.print("[dim]Hint: Type `/help` to see available local commands.[/dim]")

    # Initialize MCP
    console.print("[dim]Initializing MCP tools...[/dim]")
    await MCPManager.initialize()
    mcp_tools = MCPManager.get_tools()
    if mcp_tools:
        console.print(f"[dim]Loaded {len(mcp_tools)} MCP tools[/dim]")

    # Generate a unique thread ID for this session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    console.print(f"[dim]Session ID: {thread_id}[/dim]")

    try:
        while True:
            # Note: Prompt.ask is synchronous (blocking IO), which blocks the event loop.
            # In a production async app, we'd use an async input library or run in executor.
            # But for this simple CLI, blocking here is fine as nothing else is running in background.
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if user_input.lower() in ["exit", "quit", "/exit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # --- Slash Command Interception ---
            cmd = user_input.strip()

            if cmd == "/help":
                help_text = """
[bold]Available Commands:[/bold]
  /skills              List all available domain skills
  /load <skill_name>   Load a skill into the current context
  /exit                Quit the CLI
  /clear               (Not implemented) Clear history
"""
                console.print(Panel(help_text, title="Schaeffler CLI Help", border_style="green"))
                continue

            if cmd == "/skills":
                skills = get_all_skills()
                if not skills:
                    console.print("[yellow]No skills found in .schaeffler/skills/[/yellow]")
                else:
                    skill_list = "\n".join([f"- {s}" for s in skills])
                    console.print(Panel(skill_list, title="Available Skills", border_style="cyan"))
                continue

            if cmd.startswith("/load "):
                skill_name = cmd[6:].strip()
                if not skill_name:
                    console.print("[red]Usage: /load <skill_name>[/red]")
                    continue

                content = read_skill_content(skill_name)
                if content.startswith("Error") or content.startswith("Warning"):
                     console.print(f"[red]{content}[/red]")
                else:
                    console.print(f"[green]✓ Loaded skill: {skill_name}[/green]")
                    # Inject skill into context via a hidden HumanMessage update
                    skill_msg = f"SYSTEM UPDATE: The user has manually loaded the skill '{skill_name}'.\nContent:\n{content}\n\nPlease adhere to these guidelines for the rest of the session."

                    app_graph.update_state(config, {"messages": [HumanMessage(content=skill_msg)]})
                    console.print("[dim]Skill injected into agent memory.[/dim]")

                continue

            if not user_input.strip():
                continue

            # Stream the graph execution
            inputs = {"messages": [HumanMessage(content=user_input)], "sender": "user"}

            await _run_interaction(inputs, config)

    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
    finally:
        await MCPManager.cleanup()

async def _run_interaction(inputs: Optional[Dict[str, Any]], config: Dict[str, Any]):
    """
    Run the graph loop, handling interrupts.
    """
    try:
        # Determine if we are starting new or resuming
        # If inputs is None, we are resuming from interrupt (passing None to proceed)

        # Use astream for async streaming
        async for event in app_graph.astream(inputs, config=config, stream_mode="updates"):
            for node, values in event.items():
                if "messages" in values:
                    last_msg = values["messages"][-1]
                    sender = values.get("sender", "unknown")

                    if sender == "coder":
                        if isinstance(last_msg, AIMessage):
                            # Print thought process
                            if last_msg.content:
                                content_to_print = last_msg.content
                                if isinstance(content_to_print, list):
                                    text_parts = []
                                    for part in content_to_print:
                                        if isinstance(part, dict) and part.get('type') == 'text':
                                            text_parts.append(part.get('text', ''))
                                    content_to_print = "".join(text_parts)

                                if content_to_print:
                                    console.print(f"[bold blue][Coder][/bold blue] {content_to_print}")

                            # Print tool calls if present
                            if last_msg.tool_calls:
                                console.print(f"[bold cyan][Coder][/bold cyan] Proposed tools: {[tc['name'] for tc in last_msg.tool_calls]}")

                    elif sender == "reviewer":
                        # If reviewer sends a message, it's a rejection
                        if isinstance(last_msg, HumanMessage):
                            console.print(f"[bold red][Reviewer][/bold red] {last_msg.content}")

                    elif sender == "tools":
                         # Tool execution result
                         if isinstance(last_msg, ToolMessage):
                             content_preview = str(last_msg.content)
                             if len(content_preview) > 200:
                                 content_preview = content_preview[:200] + "..."
                             console.print(f"[bold magenta][Tool][/bold magenta] Result: {content_preview}")


        # Check if paused (HITL)
        # get_state is sync or async? MemorySaver is sync in-memory usually, but checkpointer interface supports async.
        # But app_graph.get_state(config) is a method on CompiledGraph.
        # If CompiledGraph is async, get_state is sync (it just reads checkpointer).
        snapshot = app_graph.get_state(config)

        if snapshot.next and "tools" in snapshot.next:
            # We are paused before tools
            last_msg = snapshot.values["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                tool_calls = last_msg.tool_calls

                console.print("\n[bold yellow]⚠️  Pending Tool Execution (Paused for Approval):[/bold yellow]")
                for tc in tool_calls:
                    console.print(f"  [bold]{tc['name']}[/bold]: {tc['args']}")

                # Ask for approval (Synchronous blocking)
                if Confirm.ask("Approve execution?"):
                    console.print("[green]Approving... Resuming execution.[/green]")
                    # Resume by passing None, which tells LangGraph to proceed
                    await _run_interaction(None, config)
                else:
                    console.print("[red]Rejected.[/red]")

                    # Construct rejection messages for ALL pending tool calls
                    rejection_messages = []
                    for tc in tool_calls:
                        rejection_messages.append(ToolMessage(
                            tool_call_id=tc['id'],
                            content="Error: User rejected execution.",
                            name=tc['name']
                        ))

                    # Update state to inject these tool results as if tools ran and failed
                    app_graph.update_state(config, {"messages": rejection_messages}, as_node="tools")

                    # Resume execution (will go back to Coder with the error)
                    await _run_interaction(None, config)

    except Exception as e:
        console.print(f"[bold red]Interaction Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()

@app.command()
def ping():
    """
    Verify Azure OpenAI connectivity by sending a 'Hello World' message.
    """
    console.print("[bold blue]Connecting to LLM Provider...[/bold blue]")
    try:
        llm = get_llm()
        response = llm.invoke([HumanMessage(content="Hello World")])
        console.print(f"[bold green]Response:[/bold green] {response.content}")
    except Exception as e:
        console.print(f"[bold red]Connection Failed:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
