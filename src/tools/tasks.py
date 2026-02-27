from langchain_core.tools import tool
from typing import List, Optional

from src.task_manager import add_task, complete_task, list_all_tasks

# Tools wrapper

@tool
def task_create(title: str, dependencies: Optional[List[str]] = None) -> str:
    """
    Create a new task in the project plan.
    Args:
        title: The task description.
        dependencies: Optional list of task IDs that must be completed before this task.
    """
    try:
        task = add_task(title, dependencies)
        return f"Task created: [{task.id}] {task.title}"
    except Exception as e:
        return f"Error creating task: {e}"

@tool
def task_complete(task_id: str) -> str:
    """
    Mark a task as complete.
    Args:
        task_id: The ID of the task to complete.
    """
    try:
        return complete_task(task_id)
    except Exception as e:
        return f"Error completing task: {e}"

@tool
def task_list() -> str:
    """
    List all tasks and their status.
    """
    try:
        return list_all_tasks()
    except Exception as e:
        return f"Error listing tasks: {e}"
