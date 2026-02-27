from typing import List
from pathlib import Path
from langchain_core.tools import tool

SKILLS_DIR = Path(".schaeffler/skills")

def _get_skills_dir() -> Path:
    """Ensure directory exists and return path."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    return SKILLS_DIR

def get_all_skills() -> List[str]:
    """
    Return a list of available skill names (directories).
    This function is for internal use by the CLI frontend.
    """
    skills_dir = _get_skills_dir()
    return [d.name for d in skills_dir.iterdir() if d.is_dir()]

def read_skill_content(skill_name: str) -> str:
    """
    Read the content of a skill directory.
    This function is for internal use by the CLI frontend.
    """
    # Reuse load_skill logic but without the tool wrapper overhead if needed,
    # or just call load_skill directly. For simplicity, let's reuse logic.
    return load_skill.invoke({"skill_name": skill_name})

@tool
def list_available_skills() -> str:
    """
    List all available skills (directories in .schaeffler/skills/).
    Each directory represents a skill, and may contain multiple .md files.
    Returns: A newline-separated string of skill names.
    """
    skills = get_all_skills()

    if not skills:
        return "No skills found."

    return "\n".join(skills)

@tool
def load_skill(skill_name: str) -> str:
    """
    Load all knowledge files from a specific skill directory.
    Args:
        skill_name: The name of the skill directory to load.
    Returns: The combined content of all .md files in that skill folder.
    """
    skills_dir = _get_skills_dir()
    # Security check: prevent directory traversal
    if ".." in skill_name or "/" in skill_name or "\\" in skill_name:
         return "Error: Invalid skill name."

    skill_path = skills_dir / skill_name

    if not skill_path.exists() or not skill_path.is_dir():
        return f"Error: Skill directory '{skill_name}' not found."

    try:
        content = ""
        # Read all .md files in the skill directory
        for md_file in skill_path.glob("*.md"):
             file_content = md_file.read_text(encoding="utf-8")
             content += f"\n\n--- {md_file.name} ---\n{file_content}"

        if not content:
            return f"Warning: Skill '{skill_name}' exists but contains no .md files."

        return f"<skill name=\"{skill_name}\">\n{content}\n</skill>"
    except Exception as e:
        return f"Error reading skill files: {str(e)}"
