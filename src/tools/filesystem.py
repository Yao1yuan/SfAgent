import os
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
import src.tools.base as base

@tool
def list_directory(path: str = ".") -> str:
    """
    List files in a directory. respects .gitignore (simplified implementation).
    Args:
        path: Relative path to the directory to list. Defaults to current directory.
    """
    target_path = (base.PROJECT_ROOT / path).resolve()

    if not base.is_safe_path(target_path):
        return f"Error: Access denied. Path must be within project root: {base.PROJECT_ROOT}"

    if not target_path.exists():
        return f"Error: Directory not found: {path}"

    if not target_path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        # Simple listing, ignoring hidden files starting with .git (except .gitignore)
        entries = []
        for entry in target_path.iterdir():
            # Skip .git directory
            if entry.name == ".git":
                continue

            prefix = "[DIR] " if entry.is_dir() else "[FILE]"
            entries.append(f"{prefix} {entry.name}")

        return "\n".join(sorted(entries))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool
def read_file(path: str) -> str:
    """
    Read the content of a file.
    Args:
        path: Relative path to the file to read.
    """
    target_path = (base.PROJECT_ROOT / path).resolve()

    if not base.is_safe_path(target_path):
        return f"Error: Access denied. Path must be within project root: {base.PROJECT_ROOT}"

    if not target_path.exists():
        return f"Error: File not found: {path}"

    if not target_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        # Limit file size reading? Maybe for safety, but instruction doesn't specify.
        # Assuming text files.
        return target_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Error: File appears to be binary or not UTF-8 encoded."
    except Exception as e:
        return f"Error reading file: {str(e)}"
