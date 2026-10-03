import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from google.api_core import exceptions as gexc

from app.config import settings
from llm import gemini_client
from llm.base import LLMGenerationError
from llm.coach import IdeaGenerationError, generate_idea


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    """Records the kwargs generate_content receives; optionally raises instead of returning."""

    def __init__(self, text="{}", error=None):
        self._text = text
        self._error = error
        self.calls = []

    def generate_content(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        if self._error is not None:
            raise self._error
        return _FakeResponse(self._text)


def _make_client(monkeypatch, model):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(gemini_client.genai, "configure", lambda **_: None)
    monkeypatch.setattr(gemini_client.genai, "GenerativeModel", lambda _name: model)
    return gemini_client.GeminiClient()


def test_generate_passes_explicit_timeout_and_disables_sdk_retry(monkeypatch):
    monkeypatch.setattr(settings, "gemini_timeout_sec", 12.5)
    model = _FakeModel(text='```json\n{"a": 1}\n```')
    client = _make_client(monkeypatch, model)

    assert client.generate("hello") == '{"a": 1}'

    assert len(model.calls) == 1
    _, kwargs = model.calls[0]
    assert kwargs["request_options"] == {"timeout": 12.5, "retry": None}


def test_default_timeout_is_finite_and_positive():
    assert 0 < settings.gemini_timeout_sec <= 120


def test_deadline_exceeded_becomes_llm_generation_error(monkeypatch):
    model = _FakeModel(error=gexc.DeadlineExceeded("504 Deadline Exceeded"))
    client = _make_client(monkeypatch, model)

    with pytest.raises(LLMGenerationError, match="Deadline Exceeded"):
        client.generate("hello")


def test_stalled_provider_ends_in_idea_generation_error_after_bounded_attempts(monkeypatch):
    model = _FakeModel(error=gexc.DeadlineExceeded("504 Deadline Exceeded"))
    client = _make_client(monkeypatch, model)

    with pytest.raises(IdeaGenerationError):
        generate_idea(client, "fitness", [
            {"content_type": "carousel", "hook_type": "story", "topic_tags": ["x"], "performance_z": 2.0}
        ])

    # coach.MAX_ATTEMPTS bounds the total number of provider calls per candidate.
    assert len(model.calls) == 2
    assert all(kw["request_options"]["timeout"] == settings.gemini_timeout_sec for _, kw in model.calls)
