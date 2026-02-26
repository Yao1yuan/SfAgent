from unittest.mock import patch, Mock
import pytest
from src.llm import get_llm
from langchain_openai import AzureChatOpenAI

def test_get_llm_configuration():
    """Test that the LLM is initialized with the correct parameters from settings"""
    mock_settings = Mock()
    mock_settings.azure_openai_endpoint = "https://mock.openai.azure.com"
    mock_settings.azure_openai_api_key = "mock-key"
    mock_settings.azure_openai_deployment_name = "mock-deployment"
    mock_settings.azure_openai_api_version = "2023-05-15"

    with patch('src.llm.get_settings', return_value=mock_settings):
        # We also need to patch AzureChatOpenAI because instantiation might validate the API key/endpoint format
        # or try to connect (though usually it's lazy).
        # Let's try to instantiate it. If it fails due to validation, we'll patch the class.
        # AzureChatOpenAI validates api_key and azure_endpoint
        llm = get_llm()

        assert isinstance(llm, AzureChatOpenAI)
        assert llm.azure_endpoint == "https://mock.openai.azure.com"
        assert llm.deployment_name == "mock-deployment"
        assert llm.openai_api_version == "2023-05-15"
        assert llm.temperature == 0
