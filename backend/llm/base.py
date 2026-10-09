"""Vendor-neutral interface used by the recommendation pipeline."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send prompt, return raw text response (expected to be JSON)."""
        raise NotImplementedError


class LLMGenerationError(Exception):
    """The LLM call itself failed (network, auth, rate limit, etc.) —
    distinct from a call that succeeded but returned invalid content."""
