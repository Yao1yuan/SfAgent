from langchain_core.tools import tool
import src.tools.base as base

@tool
def apply_diff_patch(path: str, search_block: str, replace_block: str) -> str:
    """
    Apply a diff patch to a file by searching for a block of text and replacing it.
    Args:
        path: Relative path to the file to modify.
        search_block: The exact block of text to search for.
        replace_block: The text to replace the search block with.
    """
    target_path = (base.PROJECT_ROOT / path).resolve()

    if not base.is_safe_path(target_path):
        return f"Error: Access denied. Path must be within project root: {base.PROJECT_ROOT}"

    if not target_path.exists():
        return f"Error: File not found: {path}"

    if not target_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        content = target_path.read_text(encoding="utf-8")

        # Check for existence
        count = content.count(search_block)

        if count == 0:
            return "Error: Search block not found in file. Please ensure exact match (including whitespace)."

        if count > 1:
            return f"Error: Ambiguous match. Search block found {count} times. Please provide more context to uniquely identify the block."

        # Perform replacement
        new_content = content.replace(search_block, replace_block)
        target_path.write_text(new_content, encoding="utf-8")

        return "Success: Patch applied successfully."

    except UnicodeDecodeError:
        return "Error: File appears to be binary or not UTF-8 encoded."
    except Exception as e:
        return f"Error applying patch: {str(e)}"
