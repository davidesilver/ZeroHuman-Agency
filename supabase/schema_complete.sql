-- ============================================================================
-- Content Engine - Complete Database Schema
-- ============================================================================
-- This file contains the complete database schema from migrations 001-033
-- Use this for a fresh database setup or reference
-- ============================================================================

-- ENABLE EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================================
-- MIGRATION 001: INITIAL SCHEMA
-- ============================================================================

-- BRANDS TABLE
CREATE TABLE IF NOT EXISTS public.brands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    industry TEXT,
    target_audience TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL
);

-- BRAND TONE OF VOICE
CREATE TABLE IF NOT EXISTS public.brand_tone_of_voice (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    tone TEXT NOT NULL,
    voice_style TEXT,
    language_style TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id)
);

-- BRAND SCORING WEIGHTS
CREATE TABLE IF NOT EXISTS public.brand_scoring_weights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    applicability_weight DECIMAL(5,2) DEFAULT 0.25 NOT NULL,
    credibility_weight DECIMAL(5,2) DEFAULT 0.20 NOT NULL,
    alignment_weight DECIMAL(5,2) DEFAULT 0.25 NOT NULL,
    trend_prediction_weight DECIMAL(5,2) DEFAULT 0.15 NOT NULL,
    italy_relevance_weight DECIMAL(5,2) DEFAULT 0.10 NOT NULL,
    feedback_bonus_weight DECIMAL(5,2) DEFAULT 0.05 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id)
);

-- BRAND SOURCES
CREATE TABLE IF NOT EXISTS public.brand_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'search', 'youtube', 'manual')),
    source_url TEXT,
    source_config JSONB,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- RESEARCH ITEMS
CREATE TABLE IF NOT EXISTS public.research_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    content TEXT,
    source_type TEXT NOT NULL,
    source_url TEXT,
    published_at TIMESTAMPTZ,
    research_run_id UUID,
    embedding vector(1536),
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'scored', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- SCORES
CREATE TABLE IF NOT EXISTS public.scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    research_item_id UUID REFERENCES public.research_items(id) ON DELETE CASCADE NOT NULL,
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    applicability_score DECIMAL(5,2) NOT NULL,
    credibility_score DECIMAL(5,2) NOT NULL,
    alignment_score DECIMAL(5,2) NOT NULL,
    trend_prediction_score DECIMAL(5,2) NOT NULL,
    italy_relevance_score DECIMAL(5,2) NOT NULL,
    feedback_bonus_score DECIMAL(5,2) DEFAULT 0.00 NOT NULL,
    total_score DECIMAL(5,2) GENERATED ALWAYS AS (
        applicability_score * 0.25 +
        credibility_score * 0.20 +
        alignment_score * 0.25 +
        trend_prediction_score * 0.15 +
        italy_relevance_score * 0.10 +
        feedback_bonus_score * 0.05
    ) STORED,
    scored_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(research_item_id, brand_id)
);

-- CONTENT DRAFTS
CREATE TABLE IF NOT EXISTS public.content_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    research_item_id UUID REFERENCES public.research_items(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('linkedin', 'twitter', 'instagram', 'facebook', 'tiktok', 'newsletter', 'blog')),
    title TEXT,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'in_review', 'approved', 'rejected', 'published', 'scheduled')),
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- GENERATION LOGS
CREATE TABLE IF NOT EXISTS public.generation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    content_draft_id UUID REFERENCES public.content_drafts(id) ON DELETE SET NULL,
    agent_type TEXT NOT NULL,
    prompt TEXT,
    response TEXT,
    tokens_used INTEGER,
    cost_usd DECIMAL(10,6),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 002: SEMANTIC DEDUP
-- ============================================================================

-- Vector similarity function for deduplication
CREATE OR REPLACE FUNCTION research_items_similarity_check(new_embedding vector, brand_id uuid)
RETURNS TABLE(id uuid, similarity float) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ri.id,
        1 - (new_embedding <=> ri.embedding) as similarity
    FROM
        research_items ri
    WHERE
        ri.brand_id = brand_id
        AND ri.embedding IS NOT NULL
        AND (1 - (new_embedding <=> ri.embedding)) > 0.95
    ORDER BY
        similarity DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRATION 004: RATE LIMIT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    endpoint TEXT NOT NULL,
    request_count INTEGER DEFAULT 0 NOT NULL,
    window_start TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    window_end TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 hour') NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id, endpoint, window_start)
);

-- ============================================================================
-- MIGRATION 005: AGENT SYSTEM
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.agent_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_key TEXT NOT NULL UNIQUE,
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    model_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.agent_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_key TEXT NOT NULL UNIQUE,
    skill_name TEXT NOT NULL,
    skill_description TEXT,
    skill_prompt TEXT NOT NULL,
    skill_type TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS public.brand_agent_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    agent_key TEXT NOT NULL,
    skill_key TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT true NOT NULL,
    priority INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id, agent_key, skill_key)
);

-- ============================================================================
-- MIGRATION 006: BRAND SCORING ENHANCEMENTS
-- ============================================================================

ALTER TABLE public.brand_scoring_weights
ADD COLUMN IF NOT EXISTS founder_principles TEXT;

-- ============================================================================
-- MIGRATION 007: ANTI-HYPE GATE COLUMNS
-- ============================================================================

ALTER TABLE public.scores
ADD COLUMN IF NOT EXISTS anti_hype_gate_score DECIMAL(5,2) DEFAULT 0.00 NOT NULL;

ALTER TABLE public.brand_scoring_weights
ADD COLUMN IF NOT EXISTS anti_hype_gate_weight DECIMAL(5,2) DEFAULT 0.00 NOT NULL;

-- ============================================================================
-- MIGRATION 008 & 009: FEEDBACK LOOP & CRON
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.content_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_draft_id UUID REFERENCES public.content_drafts(id) ON DELETE CASCADE NOT NULL,
    platform TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(content_draft_id, platform, metric_type, recorded_at)
);

-- ============================================================================
-- MIGRATION 010: PERFORMANCE OPTIMIZATION
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_research_items_brand_id ON public.research_items(brand_id);
CREATE INDEX IF NOT EXISTS idx_research_items_status ON public.research_items(status);
CREATE INDEX IF NOT EXISTS idx_research_items_created_at ON public.research_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_brand_id ON public.scores(brand_id);
CREATE INDEX IF NOT EXISTS idx_scores_total_score ON public.scores(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_content_drafts_brand_id ON public.content_drafts(brand_id);
CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON public.content_drafts(status);
CREATE INDEX IF NOT EXISTS idx_content_drafts_scheduled_for ON public.content_drafts(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_generation_logs_brand_id ON public.generation_logs(brand_id);
CREATE INDEX IF NOT EXISTS idx_generation_logs_created_at ON public.generation_logs(created_at DESC);

-- ============================================================================
-- MIGRATION 011: HUMANIZER CONTROL
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.humanizer_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    is_enabled BOOLEAN DEFAULT false NOT NULL,
    intensity_level TEXT DEFAULT 'medium' CHECK (intensity_level IN ('light', 'medium', 'strong')),
    custom_rules JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id)
);

CREATE TABLE IF NOT EXISTS public.humanizer_examples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    original_text TEXT NOT NULL,
    humanized_text TEXT NOT NULL,
    platform TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 012: LLM FALLBACK MONITORING
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.llm_fallback_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    primary_provider TEXT NOT NULL,
    fallback_provider TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    request_context JSONB,
    resolved BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 013: LLM METADATA
-- ============================================================================

ALTER TABLE public.generation_logs
ADD COLUMN IF NOT EXISTS llm_provider TEXT,
ADD COLUMN IF NOT EXISTS llm_model TEXT,
ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN DEFAULT false NOT NULL;

-- ============================================================================
-- MIGRATION 014: MANUAL RETRIEVER & SKILL DESCRIPTION
-- ============================================================================

ALTER TABLE public.brand_sources
ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE public.agent_skills
ADD COLUMN IF NOT EXISTS description TEXT;

-- ============================================================================
-- MIGRATION 015-016: BRAND SELF-SERVICE & FIXES
-- ============================================================================

ALTER TABLE public.brands
ADD COLUMN IF NOT EXISTS topics TEXT[];

ALTER TABLE public.brand_sources
ADD COLUMN IF NOT EXISTS retriever_config JSONB DEFAULT '{}'::jsonb NOT NULL;

-- ============================================================================
-- MIGRATION 017: MULTI-BRAND MEMBERSHIP
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id, user_id)
);

-- ============================================================================
-- MIGRATION 018: MEMORY LAYER
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.memory_decay (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    content_type TEXT NOT NULL,
    content_id UUID NOT NULL,
    initial_score DECIMAL(5,2) NOT NULL,
    current_score DECIMAL(5,2) NOT NULL,
    decay_rate DECIMAL(5,4) DEFAULT 0.01 NOT NULL,
    last_accessed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id, content_type, content_id)
);

-- ============================================================================
-- MIGRATION 019: WEEKLY NEWSLETTER CRON
-- ============================================================================

-- Newsletter scheduling function
CREATE OR REPLACE FUNCTION schedule_weekly_newsletters()
RETURNS void AS $$
BEGIN
    -- Logic for scheduling weekly newsletters per brand
    -- Implementation depends on business requirements
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRATION 020: RETRIEVERS ENUM EXPANSION
-- ============================================================================

ALTER TABLE public.brand_sources
ADD CONSTRAINT check_source_type
CHECK (source_type IN (
    'rss', 'search', 'youtube', 'manual',
    'semantic', 'keyword', 'practitioner',
    'trend', 'gmail', 'x', 'custom'
));

-- ============================================================================
-- MIGRATION 021: RUNTIME CONTRACT STABILIZATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.runtime_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_name TEXT NOT NULL UNIQUE,
    contract_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    contract_definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 022: BRANDS DELETE POLICY
-- ============================================================================

-- Enable cascading deletes properly
ALTER TABLE public.brand_sources DROP CONSTRAINT IF EXISTS brand_sources_brand_id_fkey;
ALTER TABLE public.brand_sources
ADD CONSTRAINT brand_sources_brand_id_fkey
FOREIGN KEY (brand_id) REFERENCES public.brands(id) ON DELETE CASCADE;

-- ============================================================================
-- MIGRATION 023: PER-BRAND DAILY BUDGET
-- ============================================================================

ALTER TABLE public.brands
ADD COLUMN IF NOT EXISTS daily_budget_usd DECIMAL(10,2) DEFAULT 10.00 NOT NULL,
ADD COLUMN IF NOT EXISTS budget_reset_at TIMESTAMPTZ DEFAULT DATE_TRUNC('day', NOW()) NOT NULL;

-- ============================================================================
-- MIGRATION 024: PER-BRAND EMAIL SETTINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_email_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    from_email TEXT NOT NULL,
    from_name TEXT NOT NULL,
    reply_to_email TEXT,
    email_provider TEXT DEFAULT 'resend' NOT NULL,
    provider_config JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id)
);

-- ============================================================================
-- MIGRATION 025: BRAND VISUAL ASSETS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_visual_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('logo', 'banner', 'profile_image', 'custom')),
    asset_url TEXT NOT NULL,
    asset_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 026: IMAGE GENERATION CONFIG
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.image_generation_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    backend TEXT DEFAULT 'mock' NOT NULL,
    model TEXT NOT NULL,
    backend_config JSONB DEFAULT '{}'::jsonb NOT NULL,
    style_preset TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id)
);

-- ============================================================================
-- MIGRATION 027: IMAGE BACKEND PROVIDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.image_backend_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,
    api_endpoint TEXT,
    auth_config JSONB DEFAULT '{}'::jsonb NOT NULL,
    supported_models JSONB DEFAULT '[]'::jsonb NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- MIGRATION 028: BRAND SOCIAL INTEGRATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_social_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES public.brands(id) ON DELETE CASCADE NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('linkedin', 'twitter', 'instagram', 'facebook', 'tiktok')),
    integration_id TEXT NOT NULL,
    integration_type TEXT NOT NULL CHECK (integration_type IN ('oauth', 'api_key', 'custom')),
    auth_config JSONB NOT NULL,
    platform_config JSONB DEFAULT '{}'::jsonb NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(brand_id, platform)
);

-- ============================================================================
-- MIGRATION 029: CONTENT DRAFTS METADATA
-- ============================================================================

ALTER TABLE public.content_drafts
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
ADD COLUMN IF NOT EXISTS generation_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS last_generated_at TIMESTAMPTZ;

-- ============================================================================
-- MIGRATION 030: AUDIT INDEXES & SEARCH PATH
-- ============================================================================

-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_research_items_embedding ON public.research_items USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_content_performance_draft_id ON public.content_performance(content_draft_id);
CREATE INDEX IF NOT EXISTS idx_content_performance_recorded_at ON public.content_performance(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_log_brand_id ON public.llm_fallback_log(brand_id);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_log_created_at ON public.llm_fallback_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_decay_brand_id ON public.memory_decay(brand_id);
CREATE INDEX IF NOT EXISTS idx_memory_decay_current_score ON public.memory_decay(current_score DESC);

-- Set search path
ALTER DATABASE postgres SET search_path TO public, extensions;

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all brand-scoped tables
ALTER TABLE public.brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_tone_of_voice ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_scoring_weights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_agent_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.humanizer_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.humanizer_examples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_fallback_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_decay ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_email_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_visual_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_generation_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_backend_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_social_integrations ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (customize based on your auth requirements)
CREATE POLICY "Users can view their own brands" ON public.brands
    FOR SELECT USING (auth.uid() = user_id OR id IN (
        SELECT brand_id FROM public.brand_memberships WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can insert their own brands" ON public.brands
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own brands" ON public.brands
    FOR UPDATE USING (auth.uid() = user_id OR id IN (
        SELECT brand_id FROM public.brand_memberships WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    ));

-- Similar policies for other tables would go here
-- (Full implementation depends on specific business logic)

-- ============================================================================
-- MIGRATION 031: RESEARCH RETRIEVER ENUM EXPANSION
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'duckduckgo'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'retriever_type')
  ) THEN
    ALTER TYPE public.retriever_type ADD VALUE 'duckduckgo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'tavily'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'retriever_type')
  ) THEN
    ALTER TYPE public.retriever_type ADD VALUE 'tavily';
  END IF;
END
$$;

-- ============================================================================
-- MIGRATION 032: BRAND DISCOVERY URLS
-- ============================================================================

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS discovery_urls text[] DEFAULT '{}';

-- ============================================================================
-- MIGRATION 033: BRAND SERVICE CREDENTIALS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_service_credentials (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  service_name    text        NOT NULL,
  encrypted_creds text        NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, service_name)
);

CREATE INDEX IF NOT EXISTS idx_bsc_brand
  ON public.brand_service_credentials (brand_id);

ALTER TABLE public.brand_service_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY bsc_select ON public.brand_service_credentials
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY bsc_insert ON public.brand_service_credentials
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY bsc_update ON public.brand_service_credentials
  FOR UPDATE USING (public.user_has_brand(brand_id))
             WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY bsc_delete ON public.brand_service_credentials
  FOR DELETE USING (public.user_has_brand(brand_id));

CREATE OR REPLACE FUNCTION public.touch_bsc_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bsc_touch
  BEFORE UPDATE ON public.brand_service_credentials
  FOR EACH ROW EXECUTE FUNCTION public.touch_bsc_updated_at();

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
