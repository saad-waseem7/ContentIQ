import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from features.topics import match_topic, normalize_topic


@pytest.mark.parametrize("typed", ["quick_recipes", "Quick Recipes", "quick recipes", "  QUICK-RECIPES ", "Quick  Recipes"])
def test_variants_of_a_topic_normalize_to_the_same_value(typed):
    assert normalize_topic(typed) == "quick_recipes"


def test_match_topic_returns_the_known_spelling():
    assert match_topic("Debt Payoff", ["transformation", "debt_payoff"]) == "debt_payoff"


def test_match_topic_returns_none_for_an_unknown_topic():
    assert match_topic("meal prep", ["transformation", "debt_payoff"]) is None


def test_match_topic_handles_known_topics_with_other_casing():
    assert match_topic("product review", ["Product Review"]) == "Product Review"
