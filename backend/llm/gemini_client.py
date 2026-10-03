"""
Concrete LLMClient backed by Google AI Studio's Gemini API. Implements the
same generate() contract as MockLLMClient — nothing in coach.py,
recommendation_service.py, idea_scoring.py, or the frontend needs to change.
"""
import re

import google.generativeai as genai

from app.config import settings
from llm.base import LLMClient, LLMGenerationError

# Gemini often wraps JSON output in markdown code fences even when told not
# to — stripped here so coach.py's json.loads() gets a clean string.
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
            # Explicit per-call deadline, and the SDK's own retry disabled: coach.py already
            # retries (MAX_ATTEMPTS), so a stalled provider is bounded to
            # MAX_ATTEMPTS * timeout instead of the SDK default of retrying for minutes.
            response = self._model.generate_content(
                prompt,
                request_options={"timeout": settings.gemini_timeout_sec, "retry": None},
            )
            text = response.text  # raises if blocked by safety filters / empty
        except Exception as e:
            raise LLMGenerationError(f"Gemini API call failed or was blocked: {e}") from e
        return _FENCE_PATTERN.sub("", text).strip()
