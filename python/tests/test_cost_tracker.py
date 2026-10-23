import pytest
from src.content_engine.utils.cost_tracker import estimate_cost, estimate_tokens

@pytest.mark.parametrize("text,expected", [
    ("", 1),
    ("a", 1),
    ("abcd", 1),
    ("abcde", 1),
    ("abcdefgh", 2),
    ("abcdefghi", 2),
    ("x" * 400, 100),
])
def test_estimate_tokens(text, expected):
    assert estimate_tokens(text) == expected

@pytest.mark.parametrize("model,tokens_input,tokens_output,expected", [
    # claude-sonnet-4-20250514: input=3.0, output=15.0 per 1M
    ("claude-sonnet-4-20250514", 1_000_000, 0, 3.0),
    ("claude-sonnet-4-20250514", 0, 1_000_000, 15.0),
    ("claude-sonnet-4-20250514", 1_000_000, 1_000_000, 18.0),
    ("claude-sonnet-4-20250514", 1_000, 500, 0.0105),

    # claude-opus-4-20250514: input=15.0, output=75.0 per 1M
    ("claude-opus-4-20250514", 1_000_000, 0, 15.0),
    ("claude-opus-4-20250514", 0, 1_000_000, 75.0),
    ("claude-opus-4-20250514", 1_000_000, 1_000_000, 90.0),

    # anthropic/claude-sonnet-4-20250514
    ("anthropic/claude-sonnet-4-20250514", 1_000_000, 1_000_000, 18.0),

    # anthropic/claude-opus-4-20250514
    ("anthropic/claude-opus-4-20250514", 1_000_000, 1_000_000, 90.0),

    # Unknown model (falls back to sonnet pricing)
    ("unknown-model", 1_000_000, 1_000_000, 18.0),

    # Zero tokens edge cases
    ("claude-sonnet-4-20250514", 0, 0, 0.0),
    ("unknown-model", 0, 0, 0.0),

    # Fractional cost rounding (rounded to 6 decimal places)
    ("claude-sonnet-4-20250514", 1, 1, 0.000018),
    ("claude-sonnet-4-20250514", 3, 0, 0.000009),
    ("claude-sonnet-4-20250514", 1, 0, 0.000003),
])
def test_estimate_cost(model, tokens_input, tokens_output, expected):
    assert estimate_cost(model, tokens_input, tokens_output) == expected
