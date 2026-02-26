import subprocess
from pathlib import Path
from langchain_core.tools import tool
import shlex
import os
import src.tools.base as base

# List of blocked commands/binaries for safety
BLOCKED_COMMANDS = [
    "rm -rf /",
    "sudo",
    "mv",
    "rm",
    "shutdown",
    "reboot",
    "mkfs",
    "dd",
    "chmod -R 777"
]

@tool
def run_shell_command(command: str) -> str:
    """
    Run a shell command safely.
    Args:
        command: The shell command to execute.
    """
    command_str = command.strip()

    # Basic blocklist check
    for blocked in BLOCKED_COMMANDS:
        if blocked in command_str:
            return f"Error: Command blocked for security reasons: {blocked}"

    # Also check if trying to access sensitive paths like /etc or ~/.ssh
    if "/etc" in command_str or "~/.ssh" in command_str:
        return "Error: Access to sensitive paths (/etc, ~/.ssh) is restricted."

    try:
        # Use subprocess.run with shell=True for convenience but with restrictions
        # However, for better security, splitting args and shell=False is preferred,
        # but user might pipe commands (e.g. ls | grep).
        # Given "Do NOT allow commands like rm -rf /", maybe allow simple commands.
        # But shell=True is needed for | and && which are common in CLI tasks.
        # Let's use shell=True but rely on the blocked list and cwd restriction.

        # Run command in project root
        result = subprocess.run(
            command_str,
            shell=True,
            cwd=base.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30  # Timeout to prevent hanging
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return f"Command failed with exit code {result.returncode}:\nStdout: {stdout}\nStderr: {stderr}"

        return stdout if stdout else "(No output)"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"
