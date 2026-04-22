"""Test suite for Content Engine — critical functions.

Tests the functions that directly impact quality, costs, and data integrity:
- _compute_final_score: wrong weights = wrong content approved/rejected
- _normalize_url + _deduplicate: missed dedup = wasted LLM calls
- _parse_json: silent fallback = garbage data in pipeline
- RateLimitState: broken limiter = unbounded LLM spend
"""

from __future__ import annotations

import json
import pytest

# ── Scoring: _compute_final_score ────────────────────────────────────────────


class TestComputeFinalScore:
    """Test the weighted scoring function."""

    def setup_method(self):
        from content_engine.scoring.engine import _compute_final_score, WEIGHTS
        from content_engine.models import ScoreResult

        self._compute = _compute_final_score
        self._weights = WEIGHTS
        self._ScoreResult = ScoreResult

    def _make_result(self, **kwargs) -> object:
        defaults = {
            "applicability": 5.0,
            "credibility": 5.0,
            "alignment": 5.0,
            "trend_prediction": 5.0,
            "italy_relevance": 5.0,
            "feedback_bonus": 5.0,
        }
        defaults.update(kwargs)
        return self._ScoreResult(**defaults)

    def test_all_fives_gives_five(self):
        """All parameters at 5.0 should yield 5.0."""
        result = self._make_result()
        assert self._compute(result) == 5.0

    def test_all_tens_gives_ten(self):
        """All parameters at 10.0 should yield 10.0."""
        result = self._make_result(
            applicability=10, credibility=10, alignment=10,
            trend_prediction=10, italy_relevance=10, feedback_bonus=10,
        )
        assert self._compute(result) == 10.0

    def test_all_zeros_gives_zero(self):
        """All parameters at 0.0 should yield 0.0."""
        result = self._make_result(
            applicability=0, credibility=0, alignment=0,
            trend_prediction=0, italy_relevance=0, feedback_bonus=0,
        )
        assert self._compute(result) == 0.0

    def test_weights_sum_to_one(self):
        """Weights must sum to 1.0 for correct normalization."""
        total = sum(self._weights.values())
        assert abs(total - 1.0) < 1e-10, f"Weights sum to {total}, expected 1.0"

    def test_applicability_dominates_over_italy(self):
        """applicability (25%) should have more impact than italy_relevance (10%)."""
        high_app = self._make_result(applicability=10, italy_relevance=0)
        high_italy = self._make_result(applicability=0, italy_relevance=10)
        assert self._compute(high_app) > self._compute(high_italy)

    def test_auto_approve_threshold(self):
        """A near-perfect score should cross the auto-approve threshold (8.0)."""
        result = self._make_result(
            applicability=9, credibility=9, alignment=9,
            trend_prediction=8, italy_relevance=7, feedback_bonus=5,
        )
        score = self._compute(result)
        assert score >= 8.0, f"Score {score} should be >= 8.0 for auto-approve"

    def test_auto_reject_threshold(self):
        """A poor score should fall below the auto-reject threshold (3.0)."""
        result = self._make_result(
            applicability=1, credibility=2, alignment=1,
            trend_prediction=2, italy_relevance=1, feedback_bonus=5,
        )
        score = self._compute(result)
        assert score <= 3.0, f"Score {score} should be <= 3.0 for auto-reject"

    def test_result_is_rounded(self):
        """Output should be rounded to 2 decimal places."""
        result = self._make_result(applicability=7.777, credibility=3.333)
        score = self._compute(result)
        assert score == round(score, 2)


# ── Research: _normalize_url + _deduplicate ──────────────────────────────────


class TestNormalizeUrl:
    """Test URL normalization for dedup."""

    def setup_method(self):
        from content_engine.orchestrator.research import _normalize_url
        self._normalize = _normalize_url

    def test_strips_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=42"
        normalized = self._normalize(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "id=42" in normalized

    def test_strips_www(self):
        url = "https://www.example.com/article"
        assert self._normalize(url) == "https://example.com/article"

    def test_strips_trailing_slash(self):
        url = "https://example.com/article/"
        assert self._normalize(url) == "https://example.com/article"

    def test_combines_all_normalizations(self):
        url1 = "https://www.example.com/article/?utm_source=google&ref=home"
        url2 = "https://example.com/article"
        assert self._normalize(url1) == self._normalize(url2)

    def test_preserves_meaningful_params(self):
        url = "https://example.com/search?q=ai+content&page=2"
        normalized = self._normalize(url)
        assert "q=" in normalized
        assert "page=" in normalized


class TestDeduplicate:
    """Test URL-based deduplication."""

    def setup_method(self):
        from content_engine.orchestrator.research import _deduplicate
        from content_engine.models import ResearchItemCreate, RetrieverType, SourceType
        self._dedup = _deduplicate
        self._Item = ResearchItemCreate
        self._RetrieverType = RetrieverType
        self._SourceType = SourceType

    def _make_item(self, url: str, title: str = "Test") -> object:
        return self._Item(
            brand_id="test-brand",
            run_id="test-run",
            retriever=self._RetrieverType.SEMANTIC,
            source_type=self._SourceType.SEARCH,
            title=title,
            url=url,
        )

    def test_removes_exact_duplicates(self):
        items = [
            self._make_item("https://example.com/a", "First"),
            self._make_item("https://example.com/a", "Duplicate"),
        ]
        result = self._dedup(items)
        assert len(result) == 1
        assert result[0].title == "First"  # keeps first seen

    def test_removes_utm_duplicates(self):
        items = [
            self._make_item("https://example.com/a"),
            self._make_item("https://example.com/a?utm_source=twitter"),
        ]
        result = self._dedup(items)
        assert len(result) == 1

    def test_removes_www_duplicates(self):
        items = [
            self._make_item("https://www.example.com/a"),
            self._make_item("https://example.com/a"),
        ]
        result = self._dedup(items)
        assert len(result) == 1

    def test_keeps_different_urls(self):
        items = [
            self._make_item("https://example.com/a"),
            self._make_item("https://example.com/b"),
            self._make_item("https://other.com/a"),
        ]
        result = self._dedup(items)
        assert len(result) == 3

    def test_empty_list(self):
        assert self._dedup([]) == []


class TestRetrieverEnums:
    """Validate transitional enum support for runtime-unblock."""

    def setup_method(self):
        from content_engine.models import RetrieverType, SourceType
        self._RetrieverType = RetrieverType
        self._SourceType = SourceType

    def test_retriever_type_accepts_new_runtime_values(self):
        assert self._RetrieverType.RSS == "rss"
        assert self._RetrieverType.YOUTUBE == "youtube"
        assert self._RetrieverType.GMAIL == "gmail"
        assert self._RetrieverType.X == "x"

    def test_source_type_matches_db_contract(self):
        assert self._SourceType.RSS == "rss"
        assert self._SourceType.SEARCH == "search"
        assert self._SourceType.YOUTUBE == "youtube"
        assert self._SourceType.SCRAPE == "scrape"


# ── GOD System: _parse_json ──────────────────────────────────────────────────


class TestParseJson:
    """Test JSON parsing with markdown fence handling."""

    def setup_method(self):
        from content_engine.agents.god_system import _parse_json
        self._parse = _parse_json

    def test_parses_plain_json(self):
        raw = '{"feedback": "good", "score": 8}'
        result = self._parse(raw)
        assert result["feedback"] == "good"
        assert result["score"] == 8

    def test_parses_json_in_code_fence(self):
        raw = '```json\n{"feedback": "good", "score": 8}\n```'
        result = self._parse(raw)
        assert result["feedback"] == "good"

    def test_parses_json_in_plain_fence(self):
        raw = '```\n{"feedback": "good"}\n```'
        result = self._parse(raw)
        assert result["feedback"] == "good"

    def test_raises_on_invalid_json(self):
        """Must raise ValueError, NOT silently return fallback."""
        with pytest.raises(ValueError, match="LLM returned invalid JSON"):
            self._parse("this is not json at all")

    def test_raises_on_partial_json(self):
        with pytest.raises(ValueError):
            self._parse('{"incomplete": ')

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError):
            self._parse("")

    def test_handles_whitespace(self):
        raw = '  \n  {"score": 7}  \n  '
        result = self._parse(raw)
        assert result["score"] == 7


# ── Rate Limiter ─────────────────────────────────────────────────────────────


class TestRateLimiter:
    """Test the sliding window rate limiter."""

    def setup_method(self):
        from content_engine.utils.rate_limiter import RateLimitState
        self._State = RateLimitState

    def test_allows_within_limit(self):
        state = self._State()
        assert state.is_allowed("test", 3, 60) is True
        assert state.is_allowed("test", 3, 60) is True
        assert state.is_allowed("test", 3, 60) is True

    def test_blocks_over_limit(self):
        state = self._State()
        for _ in range(5):
            state.is_allowed("test", 5, 60)
        assert state.is_allowed("test", 5, 60) is False

    def test_separate_keys(self):
        state = self._State()
        for _ in range(5):
            state.is_allowed("key1", 5, 60)
        # key1 is exhausted but key2 is fresh
        assert state.is_allowed("key1", 5, 60) is False
        assert state.is_allowed("key2", 5, 60) is True

    def test_limit_of_one(self):
        state = self._State()
        assert state.is_allowed("once", 1, 60) is True
        assert state.is_allowed("once", 1, 60) is False
