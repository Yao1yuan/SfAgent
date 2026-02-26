import pytest
from unittest.mock import patch, Mock
from typer.testing import CliRunner
from src.main import app
from src.llm import get_llm

runner = CliRunner()

def test_app_debug():
    """Debug test to inspect app"""
    print(f"App type: {type(app)}")
    print(f"Registered commands: {[c.name for c in app.registered_commands]}")

    # Try invoking without arguments
    result = runner.invoke(app, [])
    print(f"Invoke [] output: {result.output}")
    print(f"Invoke [] exit_code: {result.exit_code}")

    # Try invoking with --help
    result = runner.invoke(app, ["--help"])
    print(f"Invoke [--help] output: {result.output}")

def test_ping_command_success():
    """Test the ping command sends a message and prints the response"""
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "Hello there!"
    mock_llm.invoke.return_value = mock_response

    with patch('src.main.get_llm', return_value=mock_llm) as mock_get_llm:
        # runner.invoke captures stdout/stderr by default
        result = runner.invoke(app, ["ping"])

        print(f"Output: {result.output}")
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "Connecting to Azure OpenAI..." in result.output
        assert "Response: Hello there!" in result.output
        mock_get_llm.assert_called_once()

def test_chat_command_exit():
    """Test that chat command exits on 'exit' input"""
    with patch("rich.prompt.Prompt.ask", return_value="exit"):
        result = runner.invoke(app, ["chat"])
        assert result.exit_code == 0
        assert "Goodbye!" in result.output
