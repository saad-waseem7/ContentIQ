import re
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

from features.config import CTA_PATTERNS, DURATION_BUCKETS, DURATION_BUCKET_LABELS

EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]", flags=re.UNICODE
)
CTA_REGEX = re.compile("|".join(CTA_PATTERNS), flags=re.IGNORECASE)


def caption_length_chars(caption: str | None) -> int:
    return len(caption) if caption else 0


def caption_length_words(caption: str | None) -> int:
    return len(caption.split()) if caption else 0


def hashtag_count(hashtags: list[str] | None) -> int:
    return len(hashtags) if hashtags else 0


def emoji_count(text: str | None) -> int:
    return len(EMOJI_PATTERN.findall(text)) if text else 0


def has_cta(text: str | None) -> bool:
    return bool(text) and bool(CTA_REGEX.search(text))


def duration_bucket(duration_sec: int | None) -> str:
    if duration_sec is None:
        return "not_applicable"
    return pd.cut([duration_sec], bins=DURATION_BUCKETS, labels=DURATION_BUCKET_LABELS, right=False)[0]


def posting_hour(posted_at: datetime) -> int:
    return posted_at.hour


def posting_day_of_week(posted_at: datetime) -> int:
    return posted_at.weekday()  # Monday=0 .. Sunday=6, matches generator.py's own convention


def is_weekend(posted_at: datetime) -> bool:
    return posted_at.weekday() >= 5


_sentiment_analyzer = SentimentIntensityAnalyzer()

def sentiment_score(text: str | None) -> float:
    if not text:
        return 0.0
    return _sentiment_analyzer.polarity_scores(text)["compound"]