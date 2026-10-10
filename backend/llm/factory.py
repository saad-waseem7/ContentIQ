from app.config import settings
from llm.base import LLMClient
from llm.mock_client import MockLLMClient

SUPPORTED_PROVIDERS = ("mock", "gemini")


def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        from llm.gemini_client import GeminiClient

        # google-generativeai package is only required when actually selected
        return GeminiClient()
    if provider == "mock":
        return MockLLMClient()
    # A typo must not silently fall back to canned output.
    raise ValueError(f"LLM_PROVIDER must be one of {SUPPORTED_PROVIDERS}, got {settings.llm_provider!r}")