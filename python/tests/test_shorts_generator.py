from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_run_pipeline_reuses_existing_artifacts_and_completes():
    from content_engine.services import shorts_generator

    initial_state = {
        "version": 1,
        "status": "failed",
        "current_step": "b_roll",
        "inputs": {
            "topic": "How to build better videos",
            "voice_id": "voice-1",
            "pexels_keywords": ["videos"],
            "title": "Videos",
        },
        "artifacts": {
            "script": {
                "title": "Videos",
                "narration": "Videos matter.",
                "b_roll_keywords": ["video", "motion"],
            },
            "audio": {
                "path": "/tmp/already-made.mp3",
                "provider_used": "edge-tts",
                "mime_type": "audio/mpeg",
                "duration_seconds": 8.2,
                "voice_id": "voice-1",
            },
            "subtitles": [
                {"start": 0.0, "end": 1.2, "text": "Videos matter.", "words": [{"text": "Videos", "start": 0.0, "end": 0.6}, {"text": "matter.", "start": 0.62, "end": 1.2}]}
            ],
            "b_roll_urls": ["https://example.com/clip.mp4"],
            "render_props": {"topic": "How to build better videos"},
        },
        "error": "previous failure",
    }

    with patch.object(shorts_generator, "_video_row", return_value={"pipeline_state": initial_state}), \
         patch.object(shorts_generator, "_brand_theme", return_value={"brand_name": "ZeroHuman", "accent_color": "#111111", "logo_url": ""}), \
         patch.object(shorts_generator, "_generate_script", new=AsyncMock()) as mock_generate_script, \
         patch.object(shorts_generator, "synthesize_tts", new=AsyncMock()) as mock_tts, \
         patch.object(shorts_generator, "generate_subtitle_blocks", new=AsyncMock()) as mock_subtitles, \
         patch.object(shorts_generator, "search_b_roll_videos", new=AsyncMock()) as mock_b_roll, \
         patch.object(shorts_generator, "render_composition_to_path") as mock_render, \
         patch.object(shorts_generator, "_mux_audio_and_video") as mock_mux, \
         patch.object(shorts_generator, "upload_rendered_video", return_value=("https://example.com/final.mp4", "brand-1/video-1/output.mp4")) as mock_upload, \
         patch.object(shorts_generator, "_save_state") as mock_save_state:

        def _render_side_effect(*args, **kwargs):
            output_path = kwargs["output_path"]
            output_path.write_bytes(b"silent-video")

        mock_render.side_effect = _render_side_effect

        def _mux_side_effect(silent_video_path, audio_path, output_path):
            output_path.write_bytes(b"final-video")

        mock_mux.side_effect = _mux_side_effect

        result = await shorts_generator._run_pipeline(
            video_id="video-1",
            brand_id="brand-1",
            template_slug="automated-shorts",
            composition_path="compositions/automated-shorts",
            topic="How to build better videos",
            voice_id="voice-1",
            pexels_keywords=["videos"],
            title="Videos",
        )

    assert result["status"] == "completed"
    assert result["output_url"] == "https://example.com/final.mp4"
    mock_generate_script.assert_not_awaited()
    mock_tts.assert_not_awaited()
    mock_subtitles.assert_not_awaited()
    mock_b_roll.assert_not_awaited()
    mock_render.assert_called_once()
    mock_mux.assert_called_once()
    mock_upload.assert_called_once()
    assert mock_save_state.call_count > 0


def test_enqueue_shorts_generation_creates_automated_shorts_video():
    from content_engine.services import shorts_generator

    db = MagicMock()
    db.from_.return_value.insert.return_value.execute.return_value.data = [{"id": "video-1"}]

    thread = MagicMock()

    with patch.object(shorts_generator, "get_db", return_value=db), \
         patch.object(shorts_generator, "_template_row", return_value={"id": "template-1", "composition_path": "compositions/automated-shorts"}), \
         patch.object(shorts_generator.threading, "Thread", return_value=thread):

        video_id = shorts_generator.enqueue_shorts_generation(
            "brand-1",
            "A topic",
            voice_id="voice-1",
            pexels_keywords=["motion", "video"],
            title="My Short",
        )

    assert video_id == "video-1"
    db.from_.return_value.insert.assert_called_once()
    inserted = db.from_.return_value.insert.call_args.args[0]
    assert inserted["kind"] == "automated-shorts"
    assert inserted["pipeline_state"]["inputs"]["topic"] == "A topic"
    thread.start.assert_called_once()
