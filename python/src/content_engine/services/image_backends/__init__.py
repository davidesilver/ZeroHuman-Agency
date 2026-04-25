from .base import ImageBackend, GeneratedImage
from .mock_backend import MockBackend

__all__ = ["ImageBackend", "GeneratedImage", "MockBackend", "get_backend"]


def get_backend(name: str) -> ImageBackend:
    if name == "mock":
        return MockBackend()
    if name == "replicate":
        from .replicate_backend import ReplicateBackend
        return ReplicateBackend()
    if name == "openai":
        from .openai_backend import OpenAIBackend
        return OpenAIBackend()
    if name == "pillo":
        from .pillo_backend import PilloBackend
        return PilloBackend()
    if name == "openrouter":
        from .openrouter_backend import OpenRouterBackend
        return OpenRouterBackend()
    if name == "anthropic":
        from .anthropic_backend import AnthropicBackend
        return AnthropicBackend()
    raise ValueError(f"Unknown image backend: {name!r}")
