from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import get_settings

def get_llm():
    """
    Initialize the LLM based on configuration (Azure OpenAI or Gemini).
    """
    settings = get_settings()

    if settings.llm_provider.lower() == "gemini":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini provider")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            google_api_key=settings.google_api_key,
            temperature=0,
            convert_system_message_to_human=True # Gemini sometimes needs this
        )

    # Default to Azure
    if not settings.azure_openai_api_key:
        # Allow running without key if just testing CLI structure, but warn/fail if actually used
        pass

    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        temperature=0,
        streaming=True
    )
