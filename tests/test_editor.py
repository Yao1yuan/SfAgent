import pytest
from src.tools.editor import apply_diff_patch

@pytest.fixture
def editor_test_files(tmp_path, monkeypatch):
    """
    Setup for editor tests.
    """
    # Create test file
    test_file = tmp_path / "code.py"
    test_file.write_text("def hello():\n    print('hello')\n    return True\n", encoding="utf-8")

    # Patch PROJECT_ROOT in src.tools.base which is imported by editor
    monkeypatch.setattr("src.tools.base.PROJECT_ROOT", tmp_path)

    return tmp_path

def test_apply_diff_patch_success(editor_test_files):
    """Test successful patch application"""
    search = "    print('hello')\n"
    replace = "    print('world')\n"

    result = apply_diff_patch.invoke({"path": "code.py", "search_block": search, "replace_block": replace})
    assert "Success" in result

    content = (editor_test_files / "code.py").read_text(encoding="utf-8")
    assert "print('world')" in content
    assert "print('hello')" not in content

def test_apply_diff_patch_not_found(editor_test_files):
    """Test error when search block is not found"""
    search = "nonexistent"
    replace = "something"

    result = apply_diff_patch.invoke({"path": "code.py", "search_block": search, "replace_block": replace})
    assert "Error: Search block not found" in result

def test_apply_diff_patch_ambiguous(editor_test_files):
    """Test error when search block matches multiple times"""
    # Create file with duplicates
    test_file = editor_test_files / "duplicates.txt"
    test_file.write_text("line1\nline1\nline2", encoding="utf-8")

    search = "line1\n"
    replace = "lineX\n"

    result = apply_diff_patch.invoke({"path": "duplicates.txt", "search_block": search, "replace_block": replace})
    assert "Error: Ambiguous match" in result
    assert "found 2 times" in result

def test_apply_diff_patch_security(editor_test_files):
    """Test path traversal prevention"""
    result = apply_diff_patch.invoke({"path": "../outside.txt", "search_block": "a", "replace_block": "b"})
    assert "Error: Access denied" in result
