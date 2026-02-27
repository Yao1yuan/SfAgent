import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

# 1. Define a dummy completer
class TestCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        commands = ["/help", "/skills", "/load", "/exit", "/awesome-feature"]

        if text.startswith('/'):
            for cmd in commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display_meta="Test Command")

# 2. Define Style
style = Style.from_dict({
    'prompt': 'ansigreen bold',
})

async def main():
    print("Starting Interactive Prompt Test...")
    print("Type '/' to see the menu. Press TAB to complete. Type 'exit' to quit.")

    session = PromptSession(
        completer=TestCompleter(),
        style=style,
        complete_while_typing=True
    )

    while True:
        try:
            # Note: prompt_async might fail if no event loop is running properly in some envs
            # For simplicity, let's use sync prompt inside async loop (blocking but works for test)
            # Or properly await.
            user_input = await session.prompt_async(HTML('<prompt>Test-CLI ></prompt> '))
            print(f"You typed: {user_input}")
            if user_input == "exit":
                break
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ImportError:
        # Fallback for older python / no asyncio
        print("Asyncio run failed, trying sync...")
        main_sync()

def main_sync():
    session = PromptSession(completer=TestCompleter(), style=style)
    while True:
        try:
            user_input = session.prompt(HTML('<prompt>Test-CLI (Sync) ></prompt> '))
            print(f"You typed: {user_input}")
            if user_input == "exit": break
        except: break
