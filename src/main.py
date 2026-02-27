import typer
import sys
import uuid
import os
import asyncio
from typing import Optional, Dict, Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.live import Live
from rich.layout import Layout
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage, AIMessageChunk
import re

# --- 引入 prompt_toolkit 核心组件 ---
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys

# --- Global State ---
VIEW_STATE = {"detailed": False}
LAST_MSG_DATA = {"content": "", "thoughts": "", "tools": []}

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
    "/exit": "Quit the SF CLI"
}

def parse_agent_message(msg: AIMessage) -> Dict[str, Any]:
    """
    Strict Parser for reasoning models (DeepSeek-R1, OpenAI o1).
    Extracts 'thoughts' (reasoning_content or <think> tags) and 'content'.
    """
    result = {"content": "", "thoughts": "", "tools": []}

    # 1. Try to get reasoning from additional_kwargs (OpenAI o1 / DeepSeek via some providers)
    if "reasoning_content" in msg.additional_kwargs:
        result["thoughts"] = msg.additional_kwargs["reasoning_content"]

    # 2. Parse content
    raw_content = msg.content

    if isinstance(raw_content, list):
        # Handle list of dicts (Multimodal/Anthropic style)
        text_parts = []
        thinking_parts = []
        for part in raw_content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif part.get("type") == "thinking": # Claude 3.7+ potentially
                    thinking_parts.append(part.get("thinking", ""))

        full_text = "".join(text_parts)
        if thinking_parts:
            result["thoughts"] = "\n".join(thinking_parts)
    else:
        full_text = str(raw_content)

    # 3. Extract <think> tags if present in text (DeepSeek-R1 raw output)
    think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    think_match = think_pattern.search(full_text)

    if think_match:
        result["thoughts"] = think_match.group(1).strip()
        # Remove the <think> block from content
        full_text = think_pattern.sub("", full_text).strip()

    # Handle unclosed <think> tag (during streaming)
    if "<think>" in full_text and "</think>" not in full_text:
        parts = full_text.split("<think>", 1)
        # Everything after <think> is treated as thoughts until closed
        result["thoughts"] = parts[1]
        # Content is what came before
        full_text = parts[0]
    elif "</think>" in full_text and "<think>" not in full_text:
         # Closing tag appeared, but opening was likely in previous chunk (if streaming raw)
         pass

    result["content"] = full_text.strip()

    # 4. Extract Tools
    if msg.tool_calls:
        result["tools"] = msg.tool_calls

    return result

def get_live_renderable() -> Group:
    """Renderable for the Rich Live display during generation"""
    items = []

    # Default state if nothing has arrived yet
    if not LAST_MSG_DATA["thoughts"] and not LAST_MSG_DATA["content"]:
        items.append("[dim]Waiting for response...[/dim]")

    if LAST_MSG_DATA["thoughts"]:
        if VIEW_STATE["detailed"]:
             items.append(Panel(Markdown(LAST_MSG_DATA["thoughts"]), title="[bold blue]Thinking Process[/bold blue]", border_style="blue dim"))
        else:
             items.append("[dim]🤖 Coder is thinking... (Ctrl+O to expand)[/dim]")

    if LAST_MSG_DATA["content"]:
        items.append(Markdown(LAST_MSG_DATA["content"]))

    return Group(*items)

def get_dynamic_prompt():
    """
    Dynamic prompt that renders the LAST AI message + the input prompt.
    This allows the previous message to be collapsible even when waiting for input.
    """
    parts = []

    import html

    # Thoughts
    if LAST_MSG_DATA["thoughts"]:
        if VIEW_STATE["detailed"]:
            parts.append(f"<style fg='blue'><b>▾ [Thinking Process]</b></style>\n<style fg='#888888'>{html.escape(LAST_MSG_DATA['thoughts'])}</style>")
        else:
            parts.append(f"<style fg='#888888'>▸ [Thinking Process] (Ctrl+O to expand)</style>")

    # Content
    if LAST_MSG_DATA["content"]:
        content_safe = html.escape(LAST_MSG_DATA["content"])
        parts.append(f"\n<b>[Coder]</b> {content_safe}")

    parts.append("\n<ansigreen><b>You:</b></ansigreen> ")

    return HTML("\n".join(parts))

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
    SF CLI - Secure AI Developer Agent
    """
    pass

@app.command()
def chat():
    """
    Start an interactive chat session with the AI Agent.
    """
    asyncio.run(run_chat_loop())

async def run_chat_loop():
    console.print(Panel.fit("[bold blue]SF AI Developer CLI[/bold blue]\n[dim]Secure. Compliant. Autonomous.[/dim]", border_style="blue"))
    console.print("[dim]Hint: Type `/help` to see available local commands. Ctrl+O to toggle thinking.[/dim]")

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

    # Define Key Bindings for Global State Control
    kb = KeyBindings()

    @kb.add('c-o')
    def _(event):
        """Toggle detailed view"""
        VIEW_STATE["detailed"] = not VIEW_STATE["detailed"]
        event.app.invalidate()

    # 👇 [核心修改] 初始化带有自动补全功能的会话 (Session)
    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        key_bindings=kb,
        refresh_interval=0.5
    )

    try:
        while True:
            # 👇 [核心修改] 使用 prompt_toolkit 异步获取输入，支持补全和高亮
            # 这里的 prompt 是动态的，根据 LAST_MSG_DATA 和 VIEW_STATE 渲染
            try:
                user_input = await session.prompt_async(get_dynamic_prompt)
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
  Ctrl+O               Toggle Thinking Process View
"""
                console.print(Panel(help_text, title="SF CLI Help", border_style="green"))
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
    [REFACTORED] Run the graph loop with True Streaming and Background Key Listening.
    """
    global LAST_MSG_DATA

    # Only reset if starting a new turn (inputs provided)
    if inputs is not None:
        LAST_MSG_DATA = {"content": "", "thoughts": "", "tools": []}

    accumulated_msg = None

    # Create input handler for background key listening
    inp = create_input()

    try:
        # Use transient Live display so it disappears after generation
        # handing control over to get_dynamic_prompt
        with Live(get_live_renderable(), console=console, refresh_per_second=10, transient=True) as live:

            def keys_ready():
                for k in inp.read_keys():
                    if k.key == Keys.ControlO:
                        VIEW_STATE["detailed"] = not VIEW_STATE["detailed"]
                        live.update(get_live_renderable())

            # Attach input listener while streaming
            with inp.raw_mode(), inp.attach(keys_ready):
                async for event in app_graph.astream(inputs, config=config, stream_mode=["messages", "updates"]):
                    stream_type, data = event

                    # --- 模式 1：尝试抓取动态打字的碎片 (如果支持流式) ---
                    if stream_type == "messages":
                        chunk, metadata = data
                        if isinstance(chunk, (AIMessageChunk, AIMessage)):
                            if accumulated_msg is None:
                                accumulated_msg = chunk
                            else:
                                accumulated_msg += chunk

                            parsed = parse_agent_message(accumulated_msg)
                            LAST_MSG_DATA["content"] = parsed["content"]
                            LAST_MSG_DATA["thoughts"] = parsed["thoughts"]
                            LAST_MSG_DATA["tools"] = parsed.get("tools", [])

                            live.update(get_live_renderable())

                    # --- 模式 2：兜底安全网 (无论是否流式，节点执行完必触发) ---
                    elif stream_type == "updates":
                        for node, values in data.items():
                            if "messages" in values:
                                for msg in values["messages"]:
                                    if isinstance(msg, AIMessage):
                                        # 使用完整的消息覆盖状态，确保 100% 拿到结果
                                        parsed = parse_agent_message(msg)
                                        LAST_MSG_DATA["content"] = parsed["content"]
                                        LAST_MSG_DATA["thoughts"] = parsed["thoughts"]
                                        LAST_MSG_DATA["tools"] = parsed.get("tools", [])

                                        live.update(get_live_renderable())

    except KeyboardInterrupt:
        console.print("\n[bold red]🛑 Generation interrupted by user.[/bold red]")
        return
    except Exception as e:
        console.print(f"[bold red]Interaction Error:[/bold red] {e}")
        return

    # --- Step 3: Handle the Human-in-the-Loop approval ---
    snapshot = app_graph.get_state(config)
    if snapshot.next and "tools" in snapshot.next:
        last_msg = snapshot.values["messages"][-1]

        # Solidify current state before prompt (since Live is transient)
        # We print it so the user has context for what they are approving
        console.print(get_live_renderable())

        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            tool_calls = last_msg.tool_calls

            console.print("\n[bold yellow]⚠️  Pending Tool Execution (Paused for Approval):[/bold yellow]")
            for tc in tool_calls:
                console.print(f"  [bold]{tc['name']}[/bold]: {tc['args']}")

            user_approval = Prompt.ask("Approve execution? [y/n/always]", choices=["y", "n", "always"], default="y")

            if user_approval.lower() in ['y', 'yes']:
                console.print("[green]Approving... Resuming execution.[/green]")
                await _run_interaction(None, config)
            elif user_approval.lower() in ['a', 'always']:
                console.print("[green]Always-Approve Mode Enabled. Resuming...[/green]")
                await _run_interaction(None, config)
            else:
                console.print("[red]Rejected.[/red]")
                rejection_messages = [ToolMessage(tool_call_id=tc['id'], content="Error: User rejected execution.", name=tc['name']) for tc in tool_calls]
                app_graph.update_state(config, {"messages": rejection_messages}, as_node="tools")
                await _run_interaction(None, config)

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