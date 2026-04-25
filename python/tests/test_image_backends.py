import pytest
from content_engine.services.image_backends import get_backend, MockBackend


@pytest.mark.asyncio
async def test_mock_backend_returns_png_bytes():
    be = MockBackend()
    out = await be.generate(prompt="hello", negative_prompt=None,
                            model_id="mock-v1", width=512, height=512, seed=1)
    assert out.mime_type == "image/png"
    assert out.width_px == 512 and out.height_px == 512
    assert out.image_bytes.startswith(b"\x89PNG")
    assert out.cost_usd == 0.0


def test_get_backend_mock():
    be = get_backend("mock")
    assert be.name == "mock"


def test_get_backend_openrouter():
    be = get_backend("openrouter")
    assert be.name == "openrouter"


def test_get_backend_anthropic():
    be = get_backend("anthropic")
    assert be.name == "anthropic"


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError):
        get_backend("does-not-exist")
