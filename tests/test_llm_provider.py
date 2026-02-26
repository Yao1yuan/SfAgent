import pytest
import os
from unittest.mock import patch, Mock
from src.llm import get_llm
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import get_settings

# We need to ensure that the settings loading in get_llm picks up our monkeypatched env vars.
# However, pydantic-settings reads os.environ at instantiation.
# If get_settings() instantiates Settings(), it should be fine as long as os.environ is updated.
# BUT, if Settings caches or if pytest-mock/monkeypatch interaction with pydantic is tricky, we might need care.
# The previous test failed because get_llm() calls get_settings(), which reads env vars.
# Let's ensure we patch os.environ properly.

def test_get_llm_azure_provider():
    """Test initializing Azure OpenAI provider"""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "azure",
        "AZURE_OPENAI_API_KEY": "azure-key",
        "AZURE_OPENAI_ENDPOINT": "https://azure.com",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "dep",
        "AZURE_OPENAI_API_VERSION": "v1"
    }, clear=True):
        # We need to mock AzureChatOpenAI because it validates connections/keys on init
        with patch("src.llm.AzureChatOpenAI") as mock_cls:
            get_llm()
            mock_cls.assert_called_once()
            _, kwargs = mock_cls.call_args
            # Check a parameter to confirm it's using the right config
            assert kwargs["api_key"].get_secret_value() == "azure-key"

def test_get_llm_gemini_provider():
    """Test initializing Gemini provider"""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "gemini",
        "GOOGLE_API_KEY": "google-key"
    }, clear=True):
        # We need to mock ChatGoogleGenerativeAI
        with patch("src.llm.ChatGoogleGenerativeAI") as mock_cls:
            get_llm()
            mock_cls.assert_called_once()
            _, kwargs = mock_cls.call_args
            assert kwargs["model"] == "gemini-pro"
            assert kwargs["google_api_key"].get_secret_value() == "google-key"

def test_get_llm_gemini_missing_key():
    """Test Gemini failure on missing key"""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "gemini"
        # No GOOGLE_API_KEY
    }, clear=True):
         with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
             get_llm()
