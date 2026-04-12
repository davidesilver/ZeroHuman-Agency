from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    next_public_supabase_url: str = Field(alias="NEXT_PUBLIC_SUPABASE_URL")
    supabase_service_role_key: str = ""
    openrouter_api_key: str = ""
    serper_api_key: str = ""
    youtube_api_key: str = ""
    anthropic_api_key: str = ""

    # Scoring
    scoring_model: str = "anthropic/claude-sonnet-4-20250514"
    auto_approve_threshold: float = 8.0
    auto_reject_threshold: float = 3.0

    # Research
    dedup_threshold: float = 0.85
    max_items_per_retriever: int = 100

    @property
    def supabase_url(self) -> str:
        return self.next_public_supabase_url

    model_config = {"env_file": "../.env.local", "extra": "ignore", "populate_by_name": True}


settings = Settings()
