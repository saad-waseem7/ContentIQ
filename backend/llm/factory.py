from app.config import settings
from llm.base import LLMClient
from llm.mock_client import MockLLMClient


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "gemini":
        from llm.gemini_client import GeminiClient  # imported lazily so the
        # google-generativeai package is only required when actually selected
        return GeminiClient()
    return MockLLMClient()