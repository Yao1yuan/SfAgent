import pytest
import os
from pathlib import Path
from src.tools.filesystem import list_directory, read_file
from src.tools.terminal import run_shell_command

@pytest.fixture
def test_files(tmp_path, monkeypatch):
    """
    Create a temporary directory with files for testing.
    We need to monkeypatch PROJECT_ROOT in src.tools.filesystem to use tmp_path
    instead of the real project root.
    """
    # Create structure
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file2.txt").write_text("content2")

    # Patch PROJECT_ROOT in base module which is used by all tools
    monkeypatch.setattr("src.tools.base.PROJECT_ROOT", tmp_path)

    return tmp_path

def test_list_directory_success(test_files):
    """Test listing files in a directory"""
    # Use relative path '.' for root
    output = list_directory.invoke({"path": "."})
    assert "file1.txt" in output
    assert "subdir" in output
    assert "[DIR]" in output
    assert "[FILE]" in output

def test_read_file_success(test_files):
    """Test reading file content"""
    content = read_file.invoke({"path": "file1.txt"})
    assert content == "content1"

def test_path_traversal_blocked(test_files):
    """Test that accessing files outside root is blocked"""
    # Try to access parent directory
    output = read_file.invoke({"path": "../somefile"})
    assert "Error: Access denied" in output

    output = list_directory.invoke({"path": ".."})
    assert "Error: Access denied" in output

def test_run_shell_command_success(test_files):
    """Test running a simple command"""
    output = run_shell_command.invoke({"command": "echo hello"})
    assert "hello" in output.strip()

def test_run_shell_command_blocked(test_files):
    """Test blocking dangerous commands"""
    output = run_shell_command.invoke({"command": "rm -rf /"})
    assert "Error: Command blocked" in output

def test_sensitive_path_blocked(test_files):
    """Test blocking access to sensitive paths"""
    output = run_shell_command.invoke({"command": "cat /etc/passwd"})
    assert "Error: Access to sensitive paths" in output
