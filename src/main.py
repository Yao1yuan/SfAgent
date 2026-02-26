import typer
import sys
import uuid
import os
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
    console.print(Panel.fit("[bold blue]Schaeffler AI Developer CLI[/bold blue]\n[dim]Secure. Compliant. Autonomous.[/dim]", border_style="blue"))

    # Generate a unique thread ID for this session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    console.print(f"[dim]Session ID: {thread_id}[/dim]")

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if user_input.lower() in ["exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if not user_input.strip():
                continue

            # Stream the graph execution
            inputs = {"messages": [HumanMessage(content=user_input)], "sender": "user"}

            _run_interaction(inputs, config)

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")

def _run_interaction(inputs: Optional[Dict[str, Any]], config: Dict[str, Any]):
    """
    Run the graph loop, handling interrupts.
    """
    try:
        # Determine if we are starting new or resuming
        # If inputs is None, we are resuming from interrupt (passing None to proceed)
        events = app_graph.stream(inputs, config=config, stream_mode="updates")

        for event in events:
            for node, values in event.items():
                if "messages" in values:
                    last_msg = values["messages"][-1]
                    sender = values.get("sender", "unknown")

                    if sender == "coder":
                        if isinstance(last_msg, AIMessage):
                            # Print thought process
                            if last_msg.content:
                                console.print(f"[bold blue][Coder][/bold blue] {last_msg.content}")

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
                             console.print(f"[bold magenta][Tool][/bold magenta] Result: {last_msg.content[:200]}..." if len(last_msg.content) > 200 else f"[bold magenta][Tool][/bold magenta] Result: {last_msg.content}")


        # Check if paused
        snapshot = app_graph.get_state(config)

        if snapshot.next and "tools" in snapshot.next:
            # We are paused before tools
            last_msg = snapshot.values["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                tool_calls = last_msg.tool_calls

                console.print("\n[bold yellow]⚠️  Pending Tool Execution (Paused for Approval):[/bold yellow]")
                for tc in tool_calls:
                    console.print(f"  [bold]{tc['name']}[/bold]: {tc['args']}")

                # Ask for approval
                if Confirm.ask("Approve execution?"):
                    console.print("[green]Approving... Resuming execution.[/green]")
                    # Resume by passing None, which tells LangGraph to proceed
                    _run_interaction(None, config)
                else:
                    console.print("[red]Rejected.[/red]")

                    # Construct rejection messages for ALL pending tool calls
                    rejection_messages = []
                    for tc in tool_calls:
                        rejection_messages.append(ToolMessage(
                            tool_call_id=tc['id'],
                            content="Error: User rejected execution."
                        ))

                    # Update state to inject these tool results as if tools ran and failed
                    app_graph.update_state(config, {"messages": rejection_messages}, as_node="tools")

                    # Resume execution (will go back to Coder with the error)
                    _run_interaction(None, config)

    except Exception as e:
        console.print(f"[bold red]Interaction Error:[/bold red] {e}")

@app.command()
def ping():
    """
    Verify Azure OpenAI connectivity by sending a 'Hello World' message.
    """
    console.print("[bold blue]Connecting to Azure OpenAI...[/bold blue]")
    try:
        llm = get_llm()
        response = llm.invoke([HumanMessage(content="Hello World")])
        console.print(f"[bold green]Response:[/bold green] {response.content}")
    except Exception as e:
        console.print(f"[bold red]Connection Failed:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
