import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from llm.base import LLMClient, LLMGenerationError
from llm.coach import IdeaGenerationError, generate_idea
from llm.mock_client import MockLLMClient
from llm.coach import generate_ideas

GROUNDING_POSTS = [
    {"content_type": "carousel", "hook_type": "story", "topic_tags": ["transformation"], "performance_z": 2.1}
]


def test_valid_mock_response_succeeds():
    client = MockLLMClient()
    idea = generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS)
    assert idea["hook_type"] == "story"
    assert idea["content_type"] == "carousel"
    assert "2" in idea["rationale"] or any(ch.isdigit() for ch in idea["rationale"])


def test_invalid_then_valid_response_succeeds_via_retry():
    class FlakyClient(LLMClient):
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1
            if self.calls == 1:
                return "not valid json"
            return MockLLMClient().generate(prompt)

    client = FlakyClient()
    idea = generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS)
    assert client.calls == 2
    assert idea["hook_type"] == "story"


def test_persistent_bad_output_raises_after_max_attempts():
    class AlwaysBadClient(LLMClient):
        def generate(self, prompt: str) -> str:
            return "not valid json"

    with pytest.raises(IdeaGenerationError):
        generate_idea(AlwaysBadClient(), niche="fitness", grounding_posts=GROUNDING_POSTS)


def test_rejects_invalid_platform():
    client = MockLLMClient(response_overrides={"platform": "facebook"})
    with pytest.raises(IdeaGenerationError):
        generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS)


def test_rejects_rationale_with_no_digit():
    client = MockLLMClient(response_overrides={"rationale": "This will perform really well for you."})
    with pytest.raises(IdeaGenerationError):
        generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS)


def test_generate_ideas_returns_n_when_all_succeed():
    client = MockLLMClient()
    ideas = generate_ideas(client, niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)
    assert len(ideas) == 3


def test_generate_ideas_tolerates_partial_failure():
    class MostlyBadClient(LLMClient):
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1
            if self.calls == 2:
                return MockLLMClient().generate(prompt)
            return "not valid json"

    ideas = generate_ideas(MostlyBadClient(), niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)
    assert len(ideas) == 1


def test_generate_ideas_raises_when_all_fail():
    class AlwaysBadClient(LLMClient):
        def generate(self, prompt: str) -> str:
            return "not valid json"

    with pytest.raises(IdeaGenerationError):
        generate_ideas(AlwaysBadClient(), niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)        