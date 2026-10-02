"""
Deterministic mock client. Used for tests and to run the full pipeline
end-to-end with no real provider configured yet. Swappable for a real
LLMClient implementation with zero changes anywhere else — see base.py.
"""

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
        # Cite a number that is actually in the prompt, like a well-behaved real model would.
        match = re.search(r"performance_z=(-?\d+\.\d+)", prompt)
        if "rationale" not in self._overrides and match:
            response["rationale"] = (
                f"Your top matching post scored {match.group(1)} standard deviations above your own baseline."
            )
        return json.dumps(response)
