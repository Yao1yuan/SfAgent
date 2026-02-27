import json
from unittest.mock import patch, MagicMock
from src.mcp_loader import load_mcp_tools
import src.tools.base as base

def test_load_mcp_config(tmp_path, monkeypatch):
    """Test loading MCP configuration"""
    # Create fake config
    config_file = tmp_path / "sf_mcp_config.json"
    config = {
        "mcpServers": {
            "test_server": {
                "command": "echo",
                "args": ["hello"]
            }
        }
    }
    config_file.write_text(json.dumps(config), encoding="utf-8")

    # Patch project root in src.tools.base
    monkeypatch.setattr("src.tools.base.PROJECT_ROOT", tmp_path)

    # We mock the print to check if it finds the server
    # Since we didn't implement actual loading (just skeleton), we verify it reads the file.
    with patch("builtins.print") as mock_print:
        tools = load_mcp_tools()
        assert isinstance(tools, list)
        # Check if it logged finding the server
        # Depending on how print is called, we might need flexible matching
        # "Found MCP configuration for: ['test_server']"
        found = False
        for call in mock_print.call_args_list:
            if "Found MCP configuration" in str(call):
                found = True
                break
        assert found

def test_load_mcp_no_config(tmp_path, monkeypatch):
    """Test loading when config is missing"""
    monkeypatch.setattr("src.tools.base.PROJECT_ROOT", tmp_path)

    tools = load_mcp_tools()
    assert tools == []
