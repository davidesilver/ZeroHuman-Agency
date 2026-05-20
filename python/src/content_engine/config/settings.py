from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    next_public_supabase_url: str = Field("", alias="NEXT_PUBLIC_SUPABASE_URL")
    next_public_supabase_anon_key: str = Field("", alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    supabase_service_role_key: str = ""
    openrouter_api_key: str = ""
    serper_api_key: str = ""
    youtube_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    pillo_api_key: str = ""
    resend_api_key: str = ""
    firecrawl_api_key: str = ""
    tavily_api_key: str = ""
    postiz_api_key: str = ""
    postiz_base_url: str = ""
    context7_mcp_url: str = "https://mcp.context7.com/mcp"
    # Postiz MCP sidecar (antoniolg/postiz-mcp) — optional, for stateful publishing
    # Start with: npx @antoniolg/postiz-mcp  (uses POSTIZ_API_KEY + POSTIZ_BASE_URL)
    postiz_mcp_enabled: bool = False

    # Per-brand credential vault encryption key (Fernet)
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    brand_secrets_encryption_key: str = ""
    newsletter_from_email: str = "newsletter@yourdomain.com"
    newsletter_from_name: str = "Content Engine"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = ""
    dashboard_url: str = "http://localhost:3000"

    # Scoring
    scoring_model: str = "google/gemma-4-150b:free"
    auto_approve_threshold: float = 8.0
    auto_reject_threshold: float = 3.0

    # LLM Provider Preference
    use_claude_subscription: bool = False  # If TRUE, uses Claude via Anthropic API (your subscription)
                                            # If FALSE, uses OpenRouter free models (default)

    # Brand secrets encryption
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    brand_secrets_encryption_key: str = ""

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

    model_config = {"env_file": "../.env.local", "extra": "ignore", "populate_by_name": True}

    def __repr__(self) -> str:
        # Mask secret-like fields so accidental logging of the Settings
        # object (e.g. during debug) cannot leak API keys / tokens.
        secret_markers = ("api_key", "secret", "token", "service_role")
        parts: list[str] = []
        for name in self.model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and value and any(m in name.lower() for m in secret_markers):
                shown = f"***{value[-4:]}" if len(value) > 4 else "***"
                parts.append(f"{name}={shown!r}")
            else:
                parts.append(f"{name}={value!r}")
        return f"Settings({', '.join(parts)})"

    __str__ = __repr__


settings = Settings()
