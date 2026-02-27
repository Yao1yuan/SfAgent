import asyncio
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle

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
    print("Starting Interactive Prompt Test (Forced Multi-Column)...")
    print("Type '/' to see the menu. Press TAB to complete. Type 'exit' to quit.")

    # Try different complete_style options:
    # CompleteStyle.COLUMN (default list)
    # CompleteStyle.MULTI_COLUMN (grid)
    # CompleteStyle.READLINE_LIKE (horizontal)

    session = PromptSession(
        completer=TestCompleter(),
        style=style,
        complete_while_typing=True,
        complete_style=CompleteStyle.MULTI_COLUMN  # Force a visible menu style
    )

    while True:
        try:
            # Note: prompt_async might fail if no event loop is running properly in some envs
            # For simplicity, let's use sync prompt inside async loop (blocking but works for test)
            # Or properly await.
            if sys.platform == "win32":
                # On Windows, sometimes async prompt loop has issues with certain terminals
                # Let's try synchronous prompt just to test the UI rendering first
                 user_input = await session.prompt_async(HTML('<prompt>Test-CLI ></prompt> '))
            else:
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
        pass
    except Exception as e:
        print(f"Error: {e}")
