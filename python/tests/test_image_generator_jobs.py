import asyncio
from unittest.mock import MagicMock, patch
import pytest

from content_engine.services import image_generator


def _mock_db():
    """Return a MagicMock that chains through Supabase-style calls."""
    m = MagicMock()
    # Default: draft exists, brand has mock backend
    m.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "draft-1", "title": "T", "body": "B"
    }
    m.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "name": "TestBrand",
        "image_model": "mock-v1",
        "image_backend": "mock",
        "image_style_preset": "editorial-minimal",
        "image_prompt_template": None,
    }
    # insert returns a row with id
    insert_chain = m.table.return_value.insert.return_value
    insert_chain.execute.return_value.data = [{"id": "job-uuid-1"}]
    # update chain
    m.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    # storage
    m.storage.from_.return_value.upload.return_value = None
    m.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://example.com/img.png"}
    return m


@pytest.fixture(autouse=True)
def clear_semaphores():
    image_generator._brand_semaphores.clear()
    yield
    image_generator._brand_semaphores.clear()


@pytest.mark.asyncio
async def test_create_image_job_returns_pending():
    with patch.object(image_generator, "get_db", return_value=_mock_db()), \
         patch.object(image_generator, "check_daily_cost_cap", return_value=None), \
         patch.object(image_generator, "_run_image_job_with_timeout", return_value=None) as mock_run:

        result = await image_generator.create_image_job("brand-1", "draft-1", width=1024, height=1024)
        assert result["status"] == "pending"
        assert "id" in result
        # Background task should have been scheduled
        await asyncio.sleep(0.05)
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_get_image_job_returns_row():
    db = _mock_db()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "job-uuid-1",
        "status": "succeeded",
        "public_url": "https://example.com/img.png",
        "cost_usd": 0.0,
        "width_px": 1024,
        "height_px": 1024,
        "created_at": "2025-01-01T00:00:00Z",
        "started_at": "2025-01-01T00:00:01Z",
        "finished_at": "2025-01-01T00:00:05Z",
    }
    with patch.object(image_generator, "get_db", return_value=db):
        result = await image_generator.get_image_job("job-uuid-1")
        assert result["status"] == "succeeded"
        assert result["url"] == "https://example.com/img.png"


@pytest.mark.asyncio
async def test_cost_cap_creates_failed_job():
    with patch.object(image_generator, "get_db", return_value=_mock_db()), \
         patch.object(image_generator, "check_daily_cost_cap", side_effect=image_generator.CostCapExceeded("cap hit")):

        result = await image_generator.create_image_job("brand-1", "draft-1")
        assert result["status"] == "failed"
        assert "cap hit" in result["error"]
