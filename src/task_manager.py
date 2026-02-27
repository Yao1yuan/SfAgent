
import json
import uuid
import os
from typing import List, Dict, Optional, Literal
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Define Task Data Models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    status: Literal["pending", "in_progress", "blocked", "done"] = "pending"
    dependencies: List[str] = [] # List of Task IDs
    notes: Optional[str] = None

class TaskList(BaseModel):
    tasks: List[Task] = []

# Storage
TASK_FILE = Path(".schaeffler/tasks.json")

def load_tasks() -> TaskList:
    if not TASK_FILE.exists():
        return TaskList()
    try:
        content = TASK_FILE.read_text(encoding="utf-8")
        return TaskList.model_validate_json(content)
    except Exception as e:
        print(f"Error loading tasks: {e}")
        return TaskList()

def save_tasks(task_list: TaskList):
    # Ensure directory exists
    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASK_FILE.write_text(task_list.model_dump_json(indent=2), encoding="utf-8")

# Core Logic
def add_task_logic(title: str, dependencies: List[str] = None) -> Task:
    task_list_obj = load_tasks()
    new_task = Task(title=title, dependencies=dependencies or [])

    # Check if dependencies exist
    existing_ids = {t.id for t in task_list_obj.tasks}
    invalid_deps = [d for d in new_task.dependencies if d not in existing_ids]
    if invalid_deps:
        raise ValueError(f"Dependency task IDs not found: {invalid_deps}")

    if new_task.dependencies:
        # Check if deps are done
        # For simplicity, default to blocked if has deps
        new_task.status = "blocked"

    task_list_obj.tasks.append(new_task)
    save_tasks(task_list_obj)
    return new_task

def complete_task_logic(task_id: str) -> str:
    task_list_obj = load_tasks()
    target_task = next((t for t in task_list_obj.tasks if t.id == task_id), None)

    if not target_task:
        return f"Error: Task {task_id} not found."

    target_task.status = "done"

    # Check if this unblocks other tasks
    unblocked = []
    for t in task_list_obj.tasks:
        if t.status == "blocked" and task_id in t.dependencies:
            # Check if ALL deps are now done
            all_deps_done = True
            for dep_id in t.dependencies:
                dep_task = next((dt for dt in task_list_obj.tasks if dt.id == dep_id), None)
                if not dep_task or dep_task.status != "done":
                    all_deps_done = False
                    break

            if all_deps_done:
                t.status = "pending"
                unblocked.append(t.id)

    save_tasks(task_list_obj)
    msg = f"Task {task_id} ('{target_task.title}') marked as DONE."
    if unblocked:
        msg += f" Unblocked tasks: {unblocked}"
    return msg

def list_all_tasks_logic() -> str:
    task_list_obj = load_tasks()
    if not task_list_obj.tasks:
        return "No tasks found."

    output = []
    for t in task_list_obj.tasks:
        deps = f" (depends on {t.dependencies})" if t.dependencies else ""
        icon = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "blocked": "[x]",
            "done": "[v]"
        }.get(t.status, "[?]")

        output.append(f"{icon} [{t.id}] {t.title} - {t.status.upper()}{deps}")

    return "\n".join(output)

# --- Tool Definitions ---

@tool
def task_create(title: str, dependencies: List[str] = []) -> str:
    """
    Create a new task in the task list.
    Args:
        title: The description of the task.
        dependencies: Optional list of task IDs that this task depends on.
    """
    try:
        task = add_task_logic(title, dependencies)
        return f"Task created: {task.id} - {task.title}"
    except Exception as e:
        return f"Error creating task: {e}"

@tool
def task_complete(task_id: str) -> str:
    """
    Mark a task as completed.
    Args:
        task_id: The ID of the task to complete.
    """
    try:
        return complete_task_logic(task_id)
    except Exception as e:
        return f"Error completing task: {e}"

@tool
def task_list() -> str:
    """
    List all tasks and their status.
    Returns a formatted string of tasks.
    """
    try:
        return list_all_tasks_logic()
    except Exception as e:
        return f"Error listing tasks: {e}"

# Backwards compatibility if needed, though mostly we use the tools now
add_task = add_task_logic
complete_task = complete_task_logic
list_all_tasks = list_all_tasks_logic
