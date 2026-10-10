"""Gemini implementation of the shared LLMClient interface."""
import re

import google.generativeai as genai

from app.config import settings
from llm.base import LLMClient, LLMGenerationError

# Strip markdown fences that Gemini may wrap around JSON responses.
_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class GeminiClient(LLMClient):
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Get one from Google AI Studio "
                "(https://aistudio.google.com/apikey) and add it to backend/.env."
            )
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)

    def generate(self, prompt: str) -> str:
        try:
            # Let coach.py own retries; the timeout bounds each provider call.
            response = self._model.generate_content(
                prompt,
                request_options={"timeout": settings.gemini_timeout_sec, "retry": None},
            )
            text = response.text  # raises if blocked by safety filters / empty
        except Exception as e:
            raise LLMGenerationError(f"Gemini API call failed or was blocked: {e}") from e
        return _FENCE_PATTERN.sub("", text).strip()
