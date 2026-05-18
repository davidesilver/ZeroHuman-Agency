"""Tests for Humanizer Agent.

Tests critical behavior:
- Fallback on Pass 2 failure (continues with Pass 1 result)
- Behavior with empty gold_examples
- Voice calibration priority (manual > automatic > default)
- Error handling and status updates
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from content_engine.agents.humanizer import (
    humanize_draft,
    _load_voice_calibration,
    _strip_json,
    HUMANIZER_PROMPT_BASE,
    ANTI_AI_AUDIT_PROMPT,
)
from content_engine.utils.llm_client import LLMResponse


class TestVoiceCalibration:
    """Test voice calibration loading logic."""

    @pytest.fixture
    def mock_db(self):
        """Mock Supabase DB client."""
        db = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_manual_gold_examples_priority(self, mock_db):
        """Manual gold_examples in tone_of_voice should be used over automatic."""
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "tone_of_voice": {
                    "gold_examples": [
                        {"title": "Manual Example 1", "content": "This is manual content."},
                        {"title": "Manual Example 2", "content": "More manual content."},
                    ]
                }
            }
        )

        with patch("content_engine.agents.humanizer.get_db", return_value=mock_db), \
             patch("content_engine.agents.humanizer.memory_recall", new_callable=AsyncMock, return_value=[]):
            result = await _load_voice_calibration("test-brand-id")

        assert "Manual Gold Example 1" in result
        assert "Manual Example 2" in result
        assert "This is manual content." in result
        assert "# Voice Calibration (Manual Gold Examples)" in result

    @pytest.mark.asyncio
    async def test_automatic_top_performers_fallback(self, mock_db):
        """When no manual gold_examples, use top performers from content_performance."""
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"tone_of_voice": {}}
        )

        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "title": "Viral Post 1",
                    "body": "This went viral.",
                    "platform": "linkedin",
                    "engagement_score": 95.5,
                },
                {
                    "title": "Viral Post 2",
                    "body": "This also went viral.",
                    "platform": "linkedin",
                    "engagement_score": 88.2,
                },
            ]
        )

        with patch("content_engine.agents.humanizer.get_db", return_value=mock_db), \
             patch("content_engine.agents.humanizer.memory_recall", new_callable=AsyncMock, return_value=[]):
            result = await _load_voice_calibration("test-brand-id")

        assert "Viral Post 1" in result
        assert "Viral Post 2" in result
        assert "# Voice Calibration (Top Performers)" in result

    @pytest.mark.asyncio
    async def test_default_voice_fallback(self, mock_db):
        """When neither manual nor automatic data available, use default."""
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"tone_of_voice": {}}
        )

        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with patch("content_engine.agents.humanizer.get_db", return_value=mock_db), \
             patch("content_engine.agents.humanizer.memory_recall", new_callable=AsyncMock, return_value=[]):
            result = await _load_voice_calibration("test-brand-id")

        assert "# Voice Calibration\nNo samples available" in result
        assert "default natural voice" in result

    @pytest.mark.asyncio
    async def test_voice_calibration_db_error(self, mock_db):
        """Gracefully handle DB errors when loading voice calibration."""
        mock_db.table.side_effect = Exception("DB connection failed")

        with patch("content_engine.agents.humanizer.get_db", return_value=mock_db), \
             patch("content_engine.agents.humanizer.memory_recall", new_callable=AsyncMock, return_value=[]):
            result = await _load_voice_calibration("test-brand-id")

        assert "# Voice calibration unavailable" in result


class TestHumanizerDraft:
    """Test main humanize_draft function."""

    @pytest.fixture
    def mock_db(self):
        """Mock Supabase DB client."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_draft_data(self):
        """Sample draft data."""
        return {
            "id": "draft-123",
            "title": "Test Draft",
            "body": "This is AI-generated content with obvious patterns like 'in conclusion' and 'moreover'.",
            "platform": "linkedin",
            "content_type": "post",
            "version": 1,
        }

    @pytest.mark.asyncio
    async def test_successful_double_pass(self, mock_db, mock_draft_data):
        """Test successful two-pass humanization."""
        # Mock draft retrieval
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_draft_data
        )

        # Mock Pass 1 response
        pass1_response = LLMResponse(
            content=json.dumps({
                "title": "Humanized Test Draft",
                "body": "Perdere un dipendente costa il 30% dello stipendio. Non lo dico io, lo dicono i bilanci.",
                "ai_patterns_found": ["In conclusion", "Moreover"],
                "changes_summary": "Removed AI connectors and added voice",
            }),
            model_used="google/gemma-4-150b:free",
            tokens_prompt=1000,
            tokens_completion=500,
        )

        # Mock Pass 2 response
        pass2_response = LLMResponse(
            content=json.dumps({
                "remaining_ai_tells": [],
                "body": "Perdere un dipendente costa il 30% dello stipendio. Non lo dico io, lo dicono i bilanci. Ecco la realtà.",
                "audit_summary": "No remaining AI patterns detected",
            }),
            model_used="google/gemma-4-150b:free",
            tokens_prompt=800,
            tokens_completion=300,
        )

        call_llm_mock = AsyncMock(side_effect=[pass1_response, pass2_response])

        with patch("content_engine.agents.humanizer.call_llm", call_llm_mock), \
             patch("content_engine.agents.humanizer.get_agent_identity", AsyncMock(return_value="Test identity")), \
             patch("content_engine.agents.humanizer.get_db", return_value=mock_db):

            result = await humanize_draft(brand_id="brand-123", draft_id="draft-123")

        # Verify result
        assert result["draft_id"] == "draft-123"
        assert result["version"] == 2
        assert result["ai_patterns_found_count"] == 2
        assert result["remaining_ai_tells_count"] == 0

        # Verify DB was updated correctly
        update_calls = [call for call in mock_db.table.return_value.update.call_args_list]
        assert len(update_calls) >= 2  # status update + final update

        # Verify both passes were called
        assert call_llm_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_pass2_failure_fallback_to_pass1(self, mock_db, mock_draft_data):
        """Test that Pass 2 failure falls back to Pass 1 result."""
        # Mock draft retrieval
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_draft_data
        )

        # Mock Pass 1 success
        pass1_response = LLMResponse(
            content=json.dumps({
                "title": "Humanized Test Draft",
                "body": "Perdere un dipendente costa il 30% dello stipendio.",
                "ai_patterns_found": ["In conclusion"],
                "changes_summary": "Removed AI connector",
            }),
            model_used="google/gemma-4-150b:free",
            tokens_prompt=1000,
            tokens_completion=500,
        )

        # Mock Pass 2 failure
        call_llm_mock = AsyncMock(side_effect=[pass1_response, Exception("Audit failed")])

        with patch("content_engine.agents.humanizer.call_llm", call_llm_mock), \
             patch("content_engine.agents.humanizer.get_agent_identity", AsyncMock(return_value="Test identity")), \
             patch("content_engine.agents.humanizer.get_db", return_value=mock_db):

            result = await humanize_draft(brand_id="brand-123", draft_id="draft-123")

        # Verify it didn't fail completely - continued with Pass 1 result
        assert result["draft_id"] == "draft-123"
        assert result["version"] == 2
        assert result["ai_patterns_found_count"] == 1
        assert result["remaining_ai_tells_count"] == 0  # Empty because Pass 2 failed
        assert "Audit failed" in result["audit_summary"]

        # Verify DB was still updated (not marked as failed)
        update_calls = [call for call in mock_db.table.return_value.update.call_args_list]
        final_update = update_calls[-1][0][0] if update_calls else {}
        assert final_update.get("status") == "humanized"

    @pytest.mark.asyncio
    async def test_pass1_failure_marks_draft_failed(self, mock_db, mock_draft_data):
        """Test that Pass 1 failure marks draft as failed."""
        # Mock draft retrieval
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_draft_data
        )

        # Mock Pass 1 failure
        call_llm_mock = AsyncMock(side_effect=Exception("LLM service down"))

        with patch("content_engine.agents.humanizer.call_llm", call_llm_mock), \
             patch("content_engine.agents.humanizer.get_agent_identity", AsyncMock(return_value="Test identity")), \
             patch("content_engine.agents.humanizer.get_db", return_value=mock_db):

            result = await humanize_draft(brand_id="brand-123", draft_id="draft-123")

        # Verify it failed completely
        assert result["status"] == "failed"
        assert result["failed_step"] == "pass1"
        assert "LLM service down" in result["error"]

        # Verify DB was marked as failed
        update_calls = [call for call in mock_db.table.return_value.update.call_args_list]
        final_update = update_calls[-1][0][0] if update_calls else {}
        assert final_update.get("status") == "humanizer_failed"
        assert "failed_step" in final_update.get("humanizer_result", {})

    @pytest.mark.asyncio
    async def test_model_override_uses_explicit_model(self, mock_db, mock_draft_data):
        """Test that model_override bypasses default routing."""
        # Mock draft retrieval
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=mock_draft_data
        )

        # Mock responses
        pass1_response = LLMResponse(
            content=json.dumps({
                "title": "Humanized",
                "body": "Content",
                "ai_patterns_found": [],
                "changes_summary": "OK",
            }),
            model_used="anthropic/claude-3-5-haiku-20241022",
            tokens_prompt=1000,
            tokens_completion=500,
        )

        pass2_response = LLMResponse(
            content=json.dumps({
                "remaining_ai_tells": [],
                "body": "Final content",
                "audit_summary": "OK",
            }),
            model_used="anthropic/claude-3-5-haiku-20241022",
            tokens_prompt=800,
            tokens_completion=300,
        )

        # Mock call_llm (should NOT be called when model_override is set)
        call_llm_mock = AsyncMock()

        # Mock the internal _call_llm_with_model
        with patch("content_engine.agents.humanizer.call_llm", call_llm_mock), \
             patch("content_engine.agents.humanizer._call_llm_with_model", new_callable=AsyncMock) as mock_with_model, \
             patch("content_engine.agents.humanizer.get_agent_identity", AsyncMock(return_value="Test identity")), \
             patch("content_engine.agents.humanizer.get_db", return_value=mock_db):

            mock_with_model.side_effect = [pass1_response, pass2_response]

            result = await humanize_draft(
                brand_id="brand-123",
                draft_id="draft-123",
                model_override="anthropic/claude-3-5-haiku-20241022"
            )

        # Verify _call_llm_with_model was called instead of call_llm
        assert call_llm_mock.call_count == 0
        assert mock_with_model.call_count == 2

        # Verify model was passed correctly
        for call in mock_with_model.call_args_list:
            assert call[1]["model"] == "anthropic/claude-3-5-haiku-20241022"


class TestStripJson:
    """Test JSON stripping utility."""

    def test_strip_json_with_markdown_fences(self):
        """Test stripping markdown code fences."""
        raw = "```json\n{\"key\": \"value\"}\n```"
        result = _strip_json(raw)
        assert result == '{"key": "value"}'

    def test_strip_json_with_language_specified(self):
        """Test stripping markdown with language specified."""
        raw = "```python\n{\"key\": \"value\"}\n```"
        result = _strip_json(raw)
        assert result == '{"key": "value"}'

    def test_strip_json_without_fences(self):
        """Test that plain JSON is returned as-is."""
        raw = '{"key": "value"}'
        result = _strip_json(raw)
        assert result == '{"key": "value"}'

    def test_strip_json_with_newline_fence(self):
        """Test stripping when fence is on separate line."""
        raw = "```\n{\"key\": \"value\"}\n```"
        result = _strip_json(raw)
        assert result == '{"key": "value"}'


class TestPromptTemplates:
    """Test that prompt templates are correctly formatted."""

    def test_humanizer_prompt_template(self):
        """Verify humanizer prompt template has expected placeholders."""
        required_placeholders = ["platform", "content_type", "title", "body", "voice_calibration_text"]
        for placeholder in required_placeholders:
            assert f"{{{placeholder}}}" in HUMANIZER_PROMPT_BASE, f"Missing {placeholder} in prompt"

    def test_audit_prompt_template(self):
        """Verify audit prompt template has expected placeholders."""
        required_placeholders = ["title", "body"]
        for placeholder in required_placeholders:
            assert f"{{{placeholder}}}" in ANTI_AI_AUDIT_PROMPT, f"Missing {placeholder} in prompt"

    def test_humanizer_prompt_mentions_italian(self):
        """Verify humanizer prompt explicitly mentions Italian language."""
        assert "Italian" in HUMANIZER_PROMPT_BASE
