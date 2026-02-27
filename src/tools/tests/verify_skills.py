import sys
import os
from pathlib import Path

# Add project root to sys.path
# Current file is at src/tools/tests/verify_skills.py
# We want to add C:\Users\yaoyxi\Desktop\Code\SfAgent
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

try:
    from src.tools.skills import list_available_skills, load_skill
except ImportError:
    # Fallback: maybe we are just in src/tools
    sys.path.append(str(project_root / "src"))
    from tools.skills import list_available_skills, load_skill

def test_skills():
    print(f"--- Testing Skill System (Project Root: {project_root}) ---")


    # 1. Test Listing
    print("\n1. Testing list_available_skills...")
    skills = list_available_skills.invoke({})
    print(f"Result:\n{skills}")

    if "git_workflow" in skills:
        print("✅ SUCCESS: Found 'git_workflow' in skill list.")
    else:
        print("❌ FAILURE: 'git_workflow' not found.")
        return

    # 2. Test Loading
    print("\n2. Testing load_skill('git_workflow')...")
    content = load_skill.invoke({"skill_name": "git_workflow"})
    print(f"Result:\n{content}")

    if "<skill name=\"git_workflow\">" in content and "[SCH-<ticket_id>]" in content:
        print("✅ SUCCESS: Skill content loaded correctly.")
    else:
        print("❌ FAILURE: Content verification failed.")

if __name__ == "__main__":
    test_skills()
