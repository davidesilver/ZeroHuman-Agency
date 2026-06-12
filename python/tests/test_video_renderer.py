from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_render_composition_to_path_targets_repo_root_compositions(tmp_path: Path):
    from content_engine.services.video_renderer import render_composition_to_path

    output_path = tmp_path / "rendered.mp4"

    def _run(cmd, capture_output, text, timeout):
        output_path.write_bytes(b"mp4")
        return MagicMock(returncode=0, stderr="")

    with patch("content_engine.services.video_renderer.subprocess.run", side_effect=_run) as mock_run:
        render_composition_to_path(
            "compositions/weekly-recap",
            {"brand_name": "Brand"},
            output_path,
        )

    cmd = mock_run.call_args.args[0]
    assert cmd[2].endswith("/compositions/weekly-recap")
    assert output_path.exists()
