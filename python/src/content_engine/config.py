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
    postiz_base_url: str = ""
    context7_mcp_url: str = "https://mcp.context7.com/mcp"
    newsletter_from_email: str = "newsletter@yourdomain.com"
    newsletter_from_name: str = "Content Engine"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Scoring
    scoring_model: str = "google/gemma-4-150b:free"
    auto_approve_threshold: float = 8.0
    auto_reject_threshold: float = 3.0

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


settings = Settings()
