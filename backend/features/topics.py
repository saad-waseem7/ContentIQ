import re
from collections.abc import Iterable


def normalize_topic(tag: str) -> str:
    """Lowercase the tag and replace spaces or hyphens with underscores."""
    return re.sub(r"[\s\-]+", "_", tag.strip().lower())


def match_topic(tag: str, known_topics: Iterable[str]) -> str | None:
    """Returns the known topic that equals `tag` after normalization, or None."""
    wanted = normalize_topic(tag)
    for known in known_topics:
        if normalize_topic(known) == wanted:
            return known
    return None
