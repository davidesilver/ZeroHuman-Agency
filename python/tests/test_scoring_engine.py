import pytest
from content_engine.models import ScoreResult
from content_engine.scoring.engine import _compute_final_score

def test_compute_final_score():
    res = ScoreResult(
        applicability=10,
        credibility=10,
        alignment=10,
        trend_prediction=10,
        italy_relevance=10,
        feedback_bonus=0.0,
        reasoning="Perfect score"
    )
    assert _compute_final_score(res) == 9.5

    res2 = ScoreResult(
        applicability=5, # 5 * 0.25 = 1.25
        credibility=5,   # 5 * 0.20 = 1.00
        alignment=8,     # 8 * 0.25 = 2.00
        trend_prediction=2, # 2 * 0.15 = 0.30
        italy_relevance=10, # 10 * 0.10 = 1.00
        feedback_bonus=1.0, # 1 * 0.05 = 0.05
        reasoning="Mixed score"
    )
    # Sum: 1.25 + 1.00 + 2.00 + 0.30 + 1.00 + 0.05 = 5.6
    assert _compute_final_score(res2) == 5.6
