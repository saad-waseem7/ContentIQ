from app.config import settings
from llm.base import LLMClient
from llm.mock_client import MockLLMClient


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "gemini":
        from llm.gemini_client import GeminiClient

        # Keep the Gemini SDK optional for users of the mock provider.
        return GeminiClient()
    return MockLLMClient()
