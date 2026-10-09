"""Deterministic LLMClient for tests and local runs without a provider."""

import json
import re

from llm.base import LLMClient


class MockLLMClient(LLMClient):
    def __init__(self, response_overrides: dict | None = None):
        self._response = {
            "hook_type": "story",
            "content_type": "carousel",
            "platform": "instagram",
            "primary_topic_tag": "transformation",
            "duration_sec": None,
            "best_posting_window": "Tuesday 7-9pm",
            "sample_caption": "Here's the exact 90-day plan that changed everything for me.",
            "rationale": "Your last story-hook transformation posts beat your median by over 2x.",
        }
        self._overrides = response_overrides or {}
        self._response.update(self._overrides)

    def generate(self, prompt: str) -> str:
        response = dict(self._response)
        # Use a performance_z value from the prompt so the mock passes rationale grounding.
        match = re.search(r"performance_z=(-?\d+\.\d+)", prompt)
        if "rationale" not in self._overrides and match:
            response["rationale"] = (
                f"Your top matching post scored {match.group(1)} standard deviations above your own baseline."
            )
        return json.dumps(response)
