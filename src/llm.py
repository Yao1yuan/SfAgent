from langchain_openai import AzureChatOpenAI
from src.config import get_settings

def get_llm() -> AzureChatOpenAI:
    """
    Initialize the Azure OpenAI Chat model with secure settings.
    Temperature is set to 0 for maximum determinism in code generation.
    """
    settings = get_settings()

    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        temperature=0,
        streaming=True
    )
