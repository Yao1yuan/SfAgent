import pytest
from src.tools.analysis import analyze_code_structure

@pytest.fixture
def analysis_test_files(tmp_path, monkeypatch):
    """
    Setup for analysis tests.
    """
    # Create test file
    test_file = tmp_path / "example.py"
    code = """
import os

class MyClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(f"Hello {self.name}")

def utility_func(x, y):
    return x + y
"""
    test_file.write_text(code, encoding="utf-8")

    # Patch PROJECT_ROOT in src.tools.base
    monkeypatch.setattr("src.tools.base.PROJECT_ROOT", tmp_path)

    return tmp_path

def test_analyze_code_structure(analysis_test_files):
    """Test analyzing code structure"""
    result = analyze_code_structure.invoke({"path": "example.py"})

    print(f"Analysis Result:\n{result}")

    assert "class MyClass:" in result
    assert "def __init__(self, name): ..." in result
    assert "def greet(self): ..." in result
    assert "def utility_func(x, y): ..." in result
    assert "print" not in result # Implementation details should be hidden
    assert "return x + y" not in result
