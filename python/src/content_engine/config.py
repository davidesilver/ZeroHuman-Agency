from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    next_public_supabase_url: str = Field(alias="NEXT_PUBLIC_SUPABASE_URL")
    next_public_supabase_anon_key: str = Field("", alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    supabase_service_role_key: str = ""
    openrouter_api_key: str = ""
    serper_api_key: str = ""
    youtube_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    resend_api_key: str = ""
    firecrawl_api_key: str = ""
    postiz_api_key: str = ""
    postiz_api_url: str = ""   # was postiz_base_url — renamed to match POSTIZ_API_URL env var
    postiz_mode: str = "disabled"   # "self_hosted" | "cloud" | "disabled"

    # Image generation (reuse agent API keys for openrouter / anthropic)
    replicate_api_token: str = ""
    pillo_api_key: str = ""
    default_image_backend: str = "mock"      # mock | replicate | openai | pillo | openrouter | anthropic
    default_image_model: str = "mock-v1"     # per-backend model identifier

    context7_mcp_url: str = "https://mcp.context7.com/mcp"
    newsletter_from_email: str = "newsletter@yourdomain.com"
    newsletter_from_name: str = "Content Engine"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Scoring
    scoring_model: str = "google/gemma-4-150b:free"
    auto_approve_threshold: float = 8.0
    auto_reject_threshold: float = 3.0

    # LLM Provider Preference
    use_claude_subscription: bool = False  # If TRUE, uses Claude via Anthropic API (your subscription)
                                            # If FALSE, uses OpenRouter free models (default)

    # Fallback Monitoring
    fallback_alert_threshold: float = 10.0  # Alert if fallbacks exceed X% of daily calls
    fallback_daily_reset_hour: int = 0       # Hour when daily fallback counter resets (UTC)

    # Research
    dedup_threshold: float = 0.85
    max_items_per_retriever: int = 100

    @property
    def supabase_url(self) -> str:
        return self.next_public_supabase_url

    @property
    def supabase_anon_key(self) -> str:
        """Anon key for JWT verification and user-scoped DB clients (C-01/C-02)."""
        return self.next_public_supabase_anon_key

    # Any field whose name contains one of these tokens gets masked in repr().
    # Prevents credentials leaking through tracebacks, log captures, or naive
    # `print(settings)` calls.
    _SENSITIVE_TOKENS = ("key", "secret", "token", "password", "api_url")

    def __repr__(self) -> str:  # pragma: no cover - trivial
        def _mask(name: str, value: object) -> str:
            if not isinstance(value, str) or not value:
                return repr(value)
            lname = name.lower()
            if any(t in lname for t in self._SENSITIVE_TOKENS):
                if len(value) <= 8:
                    return "'***'"
                return f"'{value[:4]}…{value[-2:]}'"
            return repr(value)

        body = ", ".join(
            f"{k}={_mask(k, v)}" for k, v in self.model_dump().items()
        )
        return f"Settings({body})"

    __str__ = __repr__

    model_config = {"env_file": "../.env.local", "extra": "ignore", "populate_by_name": True}


settings = Settings()
