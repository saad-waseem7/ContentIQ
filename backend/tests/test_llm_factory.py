import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from llm import factory
from llm.mock_client import MockLLMClient


def test_mock_is_selected_case_insensitively(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_provider", " Mock ")
    assert isinstance(factory.get_llm_client(), MockLLMClient)


def test_unknown_provider_is_rejected_instead_of_falling_back_to_the_mock(monkeypatch):
    monkeypatch.setattr(factory.settings, "llm_provider", "gemin")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        factory.get_llm_client()
