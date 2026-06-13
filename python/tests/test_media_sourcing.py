from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_media_cache():
    from content_engine.services import media_sourcing

    media_sourcing._CACHE.clear()
    yield
    media_sourcing._CACHE.clear()


def _mock_db():
    db = MagicMock()
    query = db.table.return_value.select.return_value.eq.return_value.in_.return_value.like.return_value.order.return_value.limit.return_value.execute.return_value
    query.data = [{"storage_path": "brand-assets/clip-1.mp4"}]
    db.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://brand.example/clip-1.mp4"}
    return db


@pytest.mark.asyncio
async def test_search_b_roll_videos_uses_cascade_and_cache():
    from content_engine.services import media_sourcing

    db = _mock_db()

    with patch.object(media_sourcing, "get_db", return_value=db), \
         patch.object(media_sourcing, "_replicate_videos", new=AsyncMock(return_value=["https://replicate.example/clip.mp4"])) as mock_replicate, \
         patch.object(media_sourcing, "_pexels_videos", new=AsyncMock(return_value=["https://pexels.example/clip.mp4"])) as mock_pexels:

        first = await media_sourcing.search_b_roll_videos(["ai", "motion"], "brand-1", limit=3)
        second = await media_sourcing.search_b_roll_videos(["ai", "motion"], "brand-1", limit=3)

    assert first == [
        "https://brand.example/clip-1.mp4",
        "https://replicate.example/clip.mp4",
        "https://pexels.example/clip.mp4",
    ]
    assert second == first
    assert mock_replicate.call_count == 1
    assert mock_pexels.call_count == 1

