"""
Deterministic mock client. Used for tests and to run the full pipeline
end-to-end with no real provider configured yet. Swappable for a real
LLMClient implementation with zero changes anywhere else — see base.py.
"""

import json

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
        if response_overrides:
            self._response.update(response_overrides)

    def generate(self, prompt: str) -> str:
        return json.dumps(self._response)
