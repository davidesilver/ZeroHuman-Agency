import pytest
from datetime import datetime, timedelta, UTC
import math
from content_engine.services.postiz_analytics import compute_engagement_score_optimized

def test_compute_engagement_score_empty_metrics():
    """Test that empty metrics list returns the default score of 5.0"""
    assert compute_engagement_score_optimized([]) == 5.0

def test_compute_engagement_score_low_impressions():
    """Test that metrics with impressions < 100 are ignored"""
    metrics = [
        {"impressions": 99, "likes": 100, "platform": "linkedin"},
        {"impressions": 50, "likes": 50, "platform": "twitter"}
    ]
    # If all metrics are ignored, it should return 5.0
    assert compute_engagement_score_optimized(metrics) == 5.0

def test_compute_engagement_score_no_recorded_at():
    """Test that metrics without recorded_at use a default weight of 0.5"""
    metrics = [
        {"impressions": 100, "likes": 2, "platform": "linkedin"}
    ]
    # linkedin baseline is 0.02
    # rate = 2 / 100 = 0.02
    # normalized = 0.02 / 0.02 = 1.0
    # weight = 0.5
    # scored = 1.0 * 0.5 = 0.5
    # avg = 0.5
    # result = 5.0 + 0.5 * 2.5 = 6.25
    assert compute_engagement_score_optimized(metrics) == 6.25

def test_compute_engagement_score_invalid_recorded_at():
    """Test that metrics with invalid recorded_at use a default weight of 0.5"""
    metrics = [
        {"impressions": 100, "likes": 2, "platform": "linkedin", "recorded_at": "invalid-date"}
    ]
    assert compute_engagement_score_optimized(metrics) == 6.25

def test_compute_engagement_score_recent_recorded_at():
    """Test that recent metrics have a weight close to 1.0"""
    now = datetime.now(UTC)
    metrics = [
        {"impressions": 100, "likes": 2, "platform": "linkedin", "recorded_at": now.isoformat()}
    ]
    # days_ago = 0 -> weight = math.exp(0) = 1.0
    # scored = 1.0 * 1.0 = 1.0
    # avg = 1.0
    # result = 5.0 + 1.0 * 2.5 = 7.5
    assert compute_engagement_score_optimized(metrics) == 7.5

def test_compute_engagement_score_old_recorded_at():
    """Test that older metrics decay over time"""
    now = datetime.now(UTC)
    ten_days_ago = now - timedelta(days=10)
    metrics = [
        {"impressions": 100, "likes": 2, "platform": "linkedin", "recorded_at": ten_days_ago.isoformat()}
    ]
    # weight = math.exp(-0.05 * 10) = math.exp(-0.5) ≈ 0.6065
    # scored = 1.0 * math.exp(-0.5)
    # result = 5.0 + (math.exp(-0.5)) * 2.5 ≈ 6.516
    expected_weight = math.exp(-0.5)
    expected_score = 5.0 + expected_weight * 2.5
    assert math.isclose(compute_engagement_score_optimized(metrics), expected_score, rel_tol=1e-9)

def test_compute_engagement_score_platforms():
    """Test that different platforms use different baselines"""
    now = datetime.now(UTC)
    metrics = [
        {"impressions": 100, "likes": 4, "platform": "instagram", "recorded_at": now.isoformat()}
    ]
    # instagram baseline = 0.04
    # rate = 4 / 100 = 0.04
    # normalized = 0.04 / 0.04 = 1.0
    # result = 5.0 + 1.0 * 2.5 = 7.5
    assert compute_engagement_score_optimized(metrics) == 7.5

    metrics2 = [
        {"impressions": 100, "likes": 6, "platform": "tiktok", "recorded_at": now.isoformat()}
    ]
    # tiktok baseline = 0.06
    # rate = 6 / 100 = 0.06
    # normalized = 1.0
    assert compute_engagement_score_optimized(metrics2) == 7.5

def test_compute_engagement_score_high_engagement_clamping():
    """Test that exceptionally high engagement clamps at 10.0"""
    now = datetime.now(UTC)
    metrics = [
        {"impressions": 100, "likes": 50, "comments": 20, "shares": 10, "platform": "linkedin", "recorded_at": now.isoformat()}
    ]
    # weighted = 50 + 20*3 + 10*5 = 160
    # rate = 160 / 100 = 1.6
    # normalized = 1.6 / 0.02 = 80.0
    # score = 5.0 + 80.0 * 2.5 = 205.0 -> clamped to 10.0
    assert compute_engagement_score_optimized(metrics) == 10.0

def test_compute_engagement_score_low_engagement_clamping():
    """Test low engagement behavior and lower bound clamping (0.0)"""
    now = datetime.now(UTC)
    metrics = [
        {"impressions": 100, "likes": 0, "platform": "linkedin", "recorded_at": now.isoformat()}
    ]
    # rate = 0
    # normalized = 0
    # score = 5.0 + 0 * 2.5 = 5.0
    assert compute_engagement_score_optimized(metrics) == 5.0

    # It's hard to naturally reach < 0 since metrics are additive and positive.
    # But if someone hacked negative likes into the data:
    metrics_negative = [
        {"impressions": 100, "likes": -10, "platform": "linkedin", "recorded_at": now.isoformat()}
    ]
    # weighted = -10
    # rate = -0.1
    # normalized = -0.1 / 0.02 = -5.0
    # score = 5.0 + (-5.0) * 2.5 = -7.5 -> clamped to 0.0
    assert compute_engagement_score_optimized(metrics_negative) == 0.0
