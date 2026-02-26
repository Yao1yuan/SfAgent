from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class Settings(BaseSettings):
    azure_openai_api_key: Optional[SecretStr] = Field(None, validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment_name: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_DEPLOYMENT_NAME")
    azure_openai_api_version: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_API_VERSION")

    google_api_key: Optional[SecretStr] = Field(None, validation_alias="GOOGLE_API_KEY")
    llm_provider: str = Field("azure", validation_alias="LLM_PROVIDER")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Do not instantiate settings here to avoid import side effects if env vars are missing during test collection.
# Instead, users should instantiate Settings() or use a factory.
# However, for simplicity and common pattern, we can instantiate it, but wrap in try-except block
# or just let it fail if that's the desired behavior.
# Given the requirement "Implement src/config.py to load environment variables securely",
# usually a global instance is provided.
# But to make testing easier (mocking env vars), we might want a function `get_settings()`.
# For now, I'll provide the class and a lazy loader or just the class.
# The instruction says "Implement src/config.py to load environment variables".
# I'll instantiate it but allow it to fail at runtime if imported, which forces configuration to be present.

def get_settings(**kwargs) -> Settings:
    return Settings(**kwargs)
