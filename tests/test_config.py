import pytest
import os
from unittest.mock import patch
from src.config import get_settings
from pydantic import ValidationError

def test_settings_load_correctly():
    """Test that settings load correctly when env vars are present"""
    with patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "test-deployment",
        "AZURE_OPENAI_API_VERSION": "2023-05-15"
    }, clear=True):
        # Pass a non-existent env file to ensure we don't read from local .env
        settings = get_settings(_env_file="non_existent_file")
        assert settings.azure_openai_api_key.get_secret_value() == "test-key"
        assert settings.azure_openai_endpoint == "https://test.openai.azure.com"
        assert settings.azure_openai_deployment_name == "test-deployment"
        assert settings.azure_openai_api_version == "2023-05-15"

def test_settings_fail_on_missing_env():
    """Test that settings fail to load when env vars are missing"""
    # clear=True removes all env vars, ensuring they are missing
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError):
            # Pass a non-existent env file to ensure we don't read from local .env
            get_settings(_env_file="non_existent_file")
