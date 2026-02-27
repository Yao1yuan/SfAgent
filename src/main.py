import typer
import sys
import uuid
import os
import asyncio
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# --- 引入 prompt_toolkit 核心组件 ---
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import app_graph
from src.llm import get_llm
from src.mcp_loader import MCPManager
from src.tools.skills import get_all_skills, read_skill_content

# --- 自动补全器配置 (Completer) ---
COMMANDS = {
    "/help": "Show available commands",
    "/skills": "List all available domain skills",
    "/load": "Load a specific skill into context",
    "/clear": "Clear the conversation history (Not implemented)",
    "/exit": "Quit the Schaeffler CLI"
}

class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Handle command completion (starts with /)
        if text.startswith('/'):
            # If typing a skill name after /load
            if text.startswith('/load '):
                prefix = text[6:] # Extract what comes after "/load "
                available_skills = get_all_skills()

                found = False
                for skill in available_skills:
                    if skill.startswith(prefix):
                        found = True
                        yield Completion(
                            skill,
                            start_position=-len(prefix),
                            display_meta="Skill Module"
                        )
                # If no skills match, show all
                if not found and not prefix:
                    for skill in available_skills:
                         yield Completion(skill, start_position=0, display_meta="Skill Module")
                return

            # Normal command completion
            for cmd, desc in COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc
                    )

# --- CLI 主程序 ---
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

    # 👇 [核心修改] 初始化带有自动补全功能的会话 (Session)
    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True
    )

    try:
        while True:
            # 👇 [核心修改] 使用 prompt_toolkit 异步获取输入，支持补全和高亮
            try:
                user_input = await session.prompt_async(HTML('\n<ansigreen><b>You:</b></ansigreen> '))
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Session terminated by user.[/yellow]")
                break

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

    except Exception as e:
        console.print(f"\n[bold red]Fatal Error:[/bold red] {e}")
    finally:
        await MCPManager.cleanup()

async def _run_interaction(inputs: Optional[Dict[str, Any]], config: Dict[str, Any]):
    """
    Run the graph loop, handling interrupts.
    """
    try:
        async for event in app_graph.astream(inputs, config=config, stream_mode="updates"):
            for node, values in event.items():
                if "messages" in values:
                    last_msg = values["messages"][-1]
                    sender = values.get("sender", "unknown")

                    if sender == "coder":
                        if isinstance(last_msg, AIMessage):
                            # Cleanly print thought process (fixes the raw dict issue)
                            if last_msg.content:
                                content_obj = last_msg.content
                                text_parts = []
                                if isinstance(content_obj, list):
                                    for part in content_obj:
                                        if isinstance(part, dict) and part.get('type') == 'text':
                                            text_parts.append(part.get('text', ''))
                                elif isinstance(content_obj, str):
                                     text_parts.append(content_obj)

                                full_thoughts = "".join(text_parts)

                                if full_thoughts:
                                    if len(full_thoughts) <= 150:
                                        console.print(f"[bold blue][Coder][/bold blue] {full_thoughts}")
                                    else:
                                        preview = full_thoughts[:100].replace('\n', ' ') + "..."
                                        console.print(f"[bold blue][Coder][/bold blue] [dim]{preview}[/dim]")

                                        user_choice = Prompt.ask(
                                            "[dim]Press 't' to read full thoughts, or ENTER to continue[/dim]",
                                            choices=["t"],
                                            default="",
                                            show_choices=False,
                                            show_default=False
                                        )
                                        if user_choice.lower() == 't':
                                            with console.pager():
                                                console.print(Markdown(full_thoughts))

                            # Print tool calls if present
                            if last_msg.tool_calls:
                                console.print(f"[bold cyan][Coder][/bold cyan] Proposed tools: {[tc['name'] for tc in last_msg.tool_calls]}")

                    elif sender == "tools":
                         if isinstance(last_msg, ToolMessage):
                            full_content = str(last_msg.content)
                            if len(full_content) <= 300:
                                console.print(f"[bold magenta][Tool][/bold magenta] Result: {full_content}")
                            else:
                                preview = full_content[:300] + "\n... [Output Truncated] ..."
                                console.print(f"[bold magenta][Tool][/bold magenta] Result: {preview}")

                                user_choice = Prompt.ask(
                                    "[dim]Press 'v' to view full output, or ENTER to continue[/dim]",
                                    choices=["v"],
                                    default="",
                                    show_choices=False,
                                    show_default=False
                                )
                                if user_choice.lower() == 'v':
                                    with console.pager():
                                        console.print(full_content)

        # Check if paused (HITL)
        snapshot = app_graph.get_state(config)

        if snapshot.next and "tools" in snapshot.next:
            # We are paused before tools
            last_msg = snapshot.values["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                tool_calls = last_msg.tool_calls

                console.print("\n[bold yellow]⚠️  Pending Tool Execution (Paused for Approval):[/bold yellow]")
                for tc in tool_calls:
                    console.print(f"  [bold]{tc['name']}[/bold]: {tc['args']}")

                # Ask for approval (Synchronous blocking, keeps UI clean)
                if Confirm.ask("Approve execution?"):
                    console.print("[green]Approving... Resuming execution.[/green]")
                    await _run_interaction(None, config)
                else:
                    console.print("[red]Rejected.[/red]")
                    rejection_messages = []
                    for tc in tool_calls:
                        rejection_messages.append(ToolMessage(
                            tool_call_id=tc['id'],
                            content="Error: User rejected execution.",
                            name=tc['name']
                        ))
                    app_graph.update_state(config, {"messages": rejection_messages}, as_node="tools")
                    await _run_interaction(None, config)

    except Exception as e:
        console.print(f"[bold red]Interaction Error:[/bold red] {e}")

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