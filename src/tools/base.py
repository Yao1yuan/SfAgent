from pathlib import Path

# Use project root as the base for all operations
PROJECT_ROOT = Path.cwd().resolve()

def is_safe_path(path: Path) -> bool:
    """
    Verify that the path is within the project root.
    """
    try:
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(PROJECT_ROOT)
    except (ValueError, RuntimeError):
        return False
