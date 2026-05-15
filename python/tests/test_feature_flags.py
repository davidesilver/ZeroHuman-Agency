"""Unit tests for feature_flags helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetFeatureFlag:
    def test_returns_true_when_flag_is_true(self):
        from content_engine.services.feature_flags import get_feature_flag

        mock_result = MagicMock()
        mock_result.data = {"value": True}

        with patch("content_engine.services.feature_flags.get_db") as mock_db:
            mock_db.return_value.from_.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
            assert get_feature_flag("brand-1", "video_enabled") is True

    def test_returns_false_when_flag_is_false(self):
        from content_engine.services.feature_flags import get_feature_flag

        mock_result = MagicMock()
        mock_result.data = {"value": False}

        with patch("content_engine.services.feature_flags.get_db") as mock_db:
            mock_db.return_value.from_.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
            assert get_feature_flag("brand-1", "video_enabled") is False

    def test_returns_default_when_row_missing(self):
        from content_engine.services.feature_flags import get_feature_flag

        mock_result = MagicMock()
        mock_result.data = None

        with patch("content_engine.services.feature_flags.get_db") as mock_db:
            mock_db.return_value.from_.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
            assert get_feature_flag("brand-1", "unknown_flag") is False
            assert get_feature_flag("brand-1", "unknown_flag", default=True) is True

    def test_returns_default_on_exception(self):
        from content_engine.services.feature_flags import get_feature_flag

        with patch("content_engine.services.feature_flags.get_db") as mock_db:
            mock_db.side_effect = RuntimeError("DB unreachable")
            result = get_feature_flag("brand-1", "video_enabled")

        assert result is False

    def test_flag_constants_are_strings(self):
        from content_engine.services.feature_flags import (
            VIDEO_ENABLED,
            EMAIL_MARKETING_ENABLED,
            DEEP_RESEARCH_ENABLED,
            COMPETITOR_MONITORING_ENABLED,
        )
        for flag in (VIDEO_ENABLED, EMAIL_MARKETING_ENABLED, DEEP_RESEARCH_ENABLED, COMPETITOR_MONITORING_ENABLED):
            assert isinstance(flag, str)
            assert len(flag) > 0
