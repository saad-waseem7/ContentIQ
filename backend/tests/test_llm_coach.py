import sys
from pathlib import Path
from llm.coach import STRATEGY_DIRECTIVES

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
import threading
import time

from llm.base import LLMClient, LLMGenerationError
from llm.coach import IdeaGenerationError, generate_idea
from llm.mock_client import MockLLMClient
from llm.coach import generate_ideas

GROUNDING_POSTS = [
    {"content_type": "carousel", "hook_type": "story", "topic_tags": ["transformation"], "performance_z": 2.1}
]


class RecordingClient(LLMClient):
    """Thread-safe — concurrent generate_ideas() calls this from multiple
    threads simultaneously."""
    def __init__(self):
        self.prompts = []
        self._lock = threading.Lock()

    def generate(self, prompt: str) -> str:
        with self._lock:
            self.prompts.append(prompt)
        return MockLLMClient().generate(prompt)


def test_generate_ideas_assigns_a_distinct_directive_to_each_candidate():
    client = RecordingClient()
    generate_ideas(client, niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)

    assert len(client.prompts) == 3
    # Completion order isn't guaranteed under concurrency — check by set
    # membership, not position.
    for directive in STRATEGY_DIRECTIVES:
        assert any(directive in p for p in client.prompts)
    assert len(set(client.prompts)) == 3


def test_generate_ideas_cycles_directives_when_n_exceeds_directive_count():
    client = RecordingClient()
    generate_ideas(client, niche="fitness", grounding_posts=GROUNDING_POSTS, n=5)
    assert len(client.prompts) == 5
    directive_0_count = sum(1 for p in client.prompts if STRATEGY_DIRECTIVES[0] in p)
    assert directive_0_count == 2  # indices 0 and 3 (3 % 3 == 0)


def test_generate_ideas_runs_candidates_concurrently_not_sequentially():
    """Proves real wall-clock benefit, not just correctness. A client with
    a 0.1s delay per call: 3 sequential calls would take >=0.3s; concurrent
    execution should complete well under that, with generous margin for
    thread overhead to avoid flakiness."""
    class SlowClient(LLMClient):
        def generate(self, prompt: str) -> str:
            time.sleep(0.1)
            return MockLLMClient().generate(prompt)

    start = time.perf_counter()
    generate_ideas(SlowClient(), niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.25  # well under 3x0.1=0.3s sequential, comfortable margin

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


class RecordingClient(LLMClient):
    """Captures every prompt sent, so tests can verify directive text is
    actually reaching the LLM call, not just constructed and discarded."""
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return MockLLMClient().generate(prompt)


def test_generate_ideas_assigns_a_distinct_directive_to_each_candidate():
    client = RecordingClient()
    generate_ideas(client, niche="fitness", grounding_posts=GROUNDING_POSTS, n=3)

    assert len(client.prompts) == 3
    for prompt, directive in zip(client.prompts, STRATEGY_DIRECTIVES):
        assert directive in prompt

    # The three prompts must differ from each other, not just from a fixed baseline.
    assert len({p for p in client.prompts}) == 3


def test_generate_ideas_cycles_directives_when_n_exceeds_directive_count():
    client = RecordingClient()
    generate_ideas(client, niche="fitness", grounding_posts=GROUNDING_POSTS, n=5)
    assert len(client.prompts) == 5
    assert STRATEGY_DIRECTIVES[0] in client.prompts[3]  # index 3 % 3 == 0, cycled back


def test_generate_idea_still_works_without_a_directive_backward_compat():
    client = MockLLMClient()
    idea = generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS)
    assert idea["hook_type"] == "story"


def test_directive_does_not_bypass_existing_guardrail_validation():
    client = MockLLMClient(response_overrides={"platform": "facebook"})
    with pytest.raises(IdeaGenerationError):
        generate_idea(client, niche="fitness", grounding_posts=GROUNDING_POSTS, directive=STRATEGY_DIRECTIVES[0])
