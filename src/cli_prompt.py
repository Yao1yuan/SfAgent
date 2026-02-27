from prompt_toolkit.completion import Completer, Completion
from pathlib import Path
from src.tools.skills import get_all_skills

COMMANDS = {
    "/help": "Show available commands",
    "/skills": "List all available domain skills",
    "/load": "Load a specific skill into context",
    "/clear": "Clear the conversation history (Not implemented)",
    "/exit": "Quit the SF CLI"
}

class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # 1. Handle command completion (starts with /)
        if text.startswith('/'):
            # If typing a skill name after /load
            # Check if text starts with "/load " (len 6)
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
                # If no skills match, maybe show all?
                if not found and not prefix:
                    for skill in available_skills:
                         yield Completion(skill, start_position=0, display_meta="Skill Module")
                return

            # Normal command completion
            # Only yield commands that match what is typed so far
            for cmd, desc in COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc
                    )
