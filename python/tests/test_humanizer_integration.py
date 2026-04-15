"""Integration tests for Humanizer in the full pipeline.

Tests that the humanizer works correctly when:
- Called via generate_and_god_and_humanize()
- Triggered manually via API endpoint
- Skipped when disabled in brand settings
- Skipped for platforms not in humanizer_channels
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from content_engine.orchestrator.content import (
    generate_and_god_and_humanize,
    generate_and_god,
)
from content_engine.agents.humanizer import humanize_draft


@pytest.fixture
def mock_db():
    """Mock Supabase DB client."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_brand_data():
    """Sample brand data with humanizer enabled."""
    return {
        "id": "brand-123",
        "name": "Test Brand",
        "use_humanizer": True,
        "humanizer_channels": ["linkedin", "blog"],
        "humanizer_model_override": None,
        "tone_of_voice": {
            "gold_examples": [
                {
                    "title": "Example 1",
                    "content": "This is manual gold example content.",
                }
            ]
        },
    }


@pytest.fixture
def mock_draft_data():
    """Sample draft data."""
    return {
        "id": "draft-123",
        "brand_id": "brand-123",
        "title": "Test Draft",
        "body": "AI-generated content with obvious patterns.",
        "platform": "linkedin",
        "content_type": "post",
        "status": "approved",
        "version": 1,
    }


@pytest.mark.asyncio
async def test_generate_and_god_and_humanize_enabled_platform(
    mock_db, mock_brand_data, mock_draft_data
):
    """Test that humanizer runs when enabled and platform is in channels."""
    # Mock generate_and_god to return basic result
    with patch(
        "content_engine.orchestrator.content.generate_and_god",
        new_callable=AsyncMock,
    ) as mock_generate_god:
        mock_generate_god.return_value = {
            "draft_id": "draft-123",
            "version": 2,
            "god": {
                "verdict": "pass",
                "advocate_score": 8,
            },
        }

        # Mock humanizer
        with patch(
            "content_engine.orchestrator.content.humanize_draft",
            new_callable=AsyncMock,
        ) as mock_humanizer:
            mock_humanizer.return_value = {
                "draft_id": "draft-123",
                "version": 3,
                "ai_patterns_found_count": 5,
                "remaining_ai_tells_count": 0,
                "changes_summary": "Removed AI patterns",
                "audit_summary": "No remaining AI patterns",
            }

            # Mock DB calls
            mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=mock_brand_data
            )

            with patch(
                "content_engine.orchestrator.content.get_db", return_value=mock_db
            ):
                result = await generate_and_god_and_humanize(
                    brand_id="brand-123",
                    research_item_id="research-123",
                    platform="linkedin",
                    content_type="post",
                )

            # Verify humanizer was called
            mock_humanizer.assert_called_once_with(
                brand_id="brand-123",
                draft_id="draft-123",
                model_override=None,
            )

            # Verify result includes humanizer data
            assert result["humanizer"]["status"] == "completed"
            assert result["humanizer"]["ai_patterns_found_count"] == 5


@pytest.mark.asyncio
async def test_generate_and_god_and_humanize_disabled(mock_db, mock_brand_data):
    """Test that humanizer is skipped when disabled in brand settings."""
    mock_brand_data["use_humanizer"] = False

    with patch(
        "content_engine.orchestrator.content.generate_and_god",
        new_callable=AsyncMock,
    ) as mock_generate_god:
        mock_generate_god.return_value = {
            "draft_id": "draft-123",
            "version": 2,
            "god": {"verdict": "pass"},
        }

        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_brand_data
        )

        with patch(
            "content_engine.orchestrator.content.get_db", return_value=mock_db
        ):
            result = await generate_and_god_and_humanize(
                brand_id="brand-123",
                research_item_id="research-123",
                platform="linkedin",
                content_type="post",
            )

        # Verify humanizer was NOT called
        assert "humanizer" in result
        assert result["humanizer"]["status"] == "skipped"
        assert result["humanizer"]["reason"] == "disabled"


@pytest.mark.asyncio
async def test_generate_and_god_and_humanize_platform_not_enabled(
    mock_db, mock_brand_data
):
    """Test that humanizer is skipped for platforms not in humanizer_channels."""
    # Use instagram which is not in ["linkedin", "blog"]

    with patch(
        "content_engine.orchestrator.content.generate_and_god",
        new_callable=AsyncMock,
    ) as mock_generate_god:
        mock_generate_god.return_value = {
            "draft_id": "draft-123",
            "version": 2,
            "god": {"verdict": "pass"},
        }

        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_brand_data
        )

        with patch(
            "content_engine.orchestrator.content.get_db", return_value=mock_db
        ):
            result = await generate_and_god_and_humanize(
                brand_id="brand-123",
                research_item_id="research-123",
                platform="instagram",
                content_type="post",
            )

        # Verify humanizer was NOT called
        assert "humanizer" in result
        assert result["humanizer"]["status"] == "skipped"
        assert result["humanizer"]["reason"] == "platform_not_enabled"


@pytest.mark.asyncio
async def test_generate_and_god_and_humanize_god_mode_failed(mock_db, mock_brand_data):
    """Test that humanizer is skipped when GOD mode verdict is not 'pass'."""

    with patch(
        "content_engine.orchestrator.content.generate_and_god",
        new_callable=AsyncMock,
    ) as mock_generate_god:
        mock_generate_god.return_value = {
            "draft_id": "draft-123",
            "version": 2,
            "god": {"verdict": "needs_revision"},
        }

        with patch(
            "content_engine.orchestrator.content.get_db", return_value=mock_db
        ):
            result = await generate_and_god_and_humanize(
                brand_id="brand-123",
                research_item_id="research-123",
                platform="linkedin",
                content_type="post",
            )

        # Verify humanizer was NOT called because GOD mode failed
        assert "humanizer" in result
        assert result["humanizer"]["status"] == "skipped"
        assert result["humanizer"]["reason"] == "god_verdict_needs_revision"


@pytest.mark.asyncio
async def test_generate_and_god_and_humanize_with_model_override(
    mock_db, mock_brand_data
):
    """Test that model_override from brand settings is used."""
    mock_brand_data["humanizer_model_override"] = "google/gemma-4-150b:free"

    with patch(
        "content_engine.orchestrator.content.generate_and_god",
        new_callable=AsyncMock,
    ) as mock_generate_god:
        mock_generate_god.return_value = {
            "draft_id": "draft-123",
            "version": 2,
            "god": {"verdict": "pass"},
        }

        with patch(
            "content_engine.orchestrator.content.humanize_draft",
            new_callable=AsyncMock,
        ) as mock_humanizer:
            mock_humanizer.return_value = {
                "draft_id": "draft-123",
                "version": 3,
                "ai_patterns_found_count": 3,
                "remaining_ai_tells_count": 0,
                "changes_summary": "OK",
                "audit_summary": "OK",
            }

            mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=mock_brand_data
            )

            with patch(
                "content_engine.orchestrator.content.get_db", return_value=mock_db
            ):
                await generate_and_god_and_humanize(
                    brand_id="brand-123",
                    research_item_id="research-123",
                    platform="linkedin",
                    content_type="post",
                )

            # Verify model_override was passed
            mock_humanizer.assert_called_once_with(
                brand_id="brand-123",
                draft_id="draft-123",
                model_override="google/gemma-4-150b:free",
            )


@pytest.mark.asyncio
async def test_humanizer_uses_free_models_by_default(mock_db, mock_draft_data):
    """Test that humanizer uses free models when no override is set."""
    from content_engine.utils.llm_client import call_llm

    # Mock the LLM calls
    with patch(
        "content_engine.agents.humanizer.call_llm",
        new_callable=AsyncMock,
    ) as mock_call_llm:
        from content_engine.utils.llm_client import LLMResponse

        # Pass 1 response
        pass1_response = LLMResponse(
            content='{"title": "Humanized", "body": "Content", "ai_patterns_found": [], "changes_summary": "OK"}',
            model_used="google/gemma-4-150b:free",
            tokens_prompt=1000,
            tokens_completion=500,
        )

        # Pass 2 response
        pass2_response = LLMResponse(
            content='{"remaining_ai_tells": [], "body": "Final content", "audit_summary": "OK"}',
            model_used="google/gemma-4-150b:free",
            tokens_prompt=800,
            tokens_completion=300,
        )

        mock_call_llm.side_effect = [pass1_response, pass2_response]

        # Mock DB
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_draft_data
        )
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"tone_of_voice": {}}
        )

        with patch("content_engine.agents.humanizer.get_db", return_value=mock_db):
            with patch(
                "content_engine.agents.humanizer.get_agent_identity",
                new_callable=AsyncMock,
                return_value="Test identity",
            ):
                result = await humanize_draft(
                    brand_id="brand-123",
                    draft_id="draft-123",
                )

        # Verify both calls used task_type="creative" which routes to free models
        assert mock_call_llm.call_count == 2
        for call in mock_call_llm.call_args_list:
            assert call[1]["task_type"] == "creative"  # Routes to Gemma 4 free → Haiku

        # Verify result
        assert result["draft_id"] == "draft-123"
        assert result["status"] == "humanized"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
