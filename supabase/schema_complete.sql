-- ============================================================================
-- ZeroHuman Agency — Complete Database Schema
-- ============================================================================
-- Generated: 2026-05-19
-- Consolidated from migrations 001–042 (49 files, deduplicated)
--
-- This is the SINGLE SOURCE OF TRUTH for the database schema.
-- Run on a fresh Supabase instance to bootstrap everything.
--
-- Sections:
--   §1  Extensions
--   §2  Enum types
--   §3  Helper functions
--   §4  Core tables (brands, users, research, scoring, content)
--   §5  Agent system
--   §6  Feedback loop & social metrics
--   §7  Humanizer
--   §8  LLM fallback monitoring
--   §9  Multi-brand membership (brand_members)
--   §10 Memory layer
--   §11 Brand assets & image generation
--   §12 Feature flags
--   §13 Brand integrations (consolidated credentials)
--   §14 Email & newsletter extensions
--   §15 Deep research
--   §16 Competitor watch
--   §17 Notification events
--   §18 Video system
--   §19 Brevo (contacts + campaigns)
--   §20 Email automations
--   §21 Views
--   §22 RLS policies
--   §23 Storage buckets
--   §24 Cron jobs
--   §25 Seed data
--   §26 Grants
-- ============================================================================

SET search_path TO public, extensions;

-- ============================================================================
-- §1  EXTENSIONS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector      WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ============================================================================
-- §2  ENUM TYPES
-- ============================================================================

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
  CREATE TYPE user_role AS ENUM ('owner', 'editor', 'viewer');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'run_status') THEN
  CREATE TYPE run_status AS ENUM ('running', 'completed', 'failed');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type') THEN
  CREATE TYPE source_type AS ENUM ('rss', 'search', 'youtube', 'scrape');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'retriever_type') THEN
  CREATE TYPE retriever_type AS ENUM (
    'semantic', 'practitioner', 'trusted_source', 'keyword', 'trend',
    'duckduckgo', 'tavily', 'deep_research'
  );
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_status') THEN
  CREATE TYPE item_status AS ENUM ('new', 'scored', 'approved', 'rejected', 'archived');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_type') THEN
  CREATE TYPE content_type AS ENUM (
    'post', 'blog', 'newsletter_section', 'carousel', 'video_script', 'thread'
  );
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'platform') THEN
  CREATE TYPE platform AS ENUM (
    'linkedin', 'instagram', 'facebook', 'x', 'tiktok', 'blog', 'newsletter'
  );
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'draft_status') THEN
  CREATE TYPE draft_status AS ENUM (
    'draft', 'in_review', 'god_mode', 'approved', 'scheduled', 'published', 'archived'
  );
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'god_verdict') THEN
  CREATE TYPE god_verdict AS ENUM ('pass', 'needs_revision', 'reject');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newsletter_status') THEN
  CREATE TYPE newsletter_status AS ENUM ('draft', 'in_review', 'approved', 'scheduled', 'sent');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'slot_type') THEN
  CREATE TYPE slot_type AS ENUM ('sistema', 'strumento_lampo', 'mossa');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_status') THEN
  CREATE TYPE campaign_status AS ENUM ('draft', 'scheduled', 'publishing', 'completed', 'failed');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type') THEN
  CREATE TYPE event_type AS ENUM ('newsletter', 'social', 'blog_video', 'sponsorship');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_status') THEN
  CREATE TYPE event_status AS ENUM ('planned', 'confirmed', 'published');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lab_status') THEN
  CREATE TYPE lab_status AS ENUM ('active', 'completed', 'paused');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'round_winner') THEN
  CREATE TYPE round_winner AS ENUM ('champion', 'challenger', 'draw');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_type') THEN
  CREATE TYPE deal_type AS ENUM ('sponsorship', 'affiliate', 'newsletter_feature', 'product');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recurrence_type') THEN
  CREATE TYPE recurrence_type AS ENUM ('one_time', 'monthly', 'quarterly');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_status') THEN
  CREATE TYPE deal_status AS ENUM ('proposal', 'negotiation', 'confirmed', 'active', 'completed', 'cancelled');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'health_status') THEN
  CREATE TYPE health_status AS ENUM ('healthy', 'degraded', 'down');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_type') THEN
  CREATE TYPE feedback_type AS ENUM ('like', 'dislike', 'top_pick', 'comment');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_source') THEN
  CREATE TYPE feedback_source AS ENUM ('manual', 'writing_lab', 'analytics');
END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'memory_tier') THEN
  CREATE TYPE memory_tier AS ENUM ('core', 'persistent', 'standard', 'transient');
END IF; END $$;

-- ============================================================================
-- §3  HELPER FUNCTIONS
-- ============================================================================

-- Generic updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

-- Generic touch_updated_at (used by video, brevo, automations)
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

-- Memory TTL helper
CREATE OR REPLACE FUNCTION memory_ttl(p_tier memory_tier)
RETURNS interval LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE p_tier
    WHEN 'core'       THEN NULL
    WHEN 'persistent' THEN interval '365 days'
    WHEN 'standard'   THEN interval '90 days'
    WHEN 'transient'  THEN interval '7 days'
  END
$$;


-- ============================================================================
-- §4  CORE TABLES
-- ============================================================================

-- ── brands ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brands (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                    text        NOT NULL,
  slug                    text        NOT NULL UNIQUE,
  topics                  text[]      DEFAULT '{}',
  tone_of_voice           jsonb       DEFAULT '{}',
  scoring_weights         jsonb       DEFAULT '{}',
  rss_sources             jsonb       DEFAULT '[]',
  social_accounts         jsonb       DEFAULT '{}',
  -- 007: anti-hype few-shot examples
  gold_examples           text[]      DEFAULT '{}',
  discard_examples        text[]      DEFAULT '{}',
  -- 011: humanizer control
  use_humanizer           boolean     DEFAULT false,
  humanizer_channels      text[]      DEFAULT ARRAY['linkedin', 'blog'],
  humanizer_model_override text,
  -- 023: per-brand daily budget
  daily_budget_usd        numeric(10,4) DEFAULT NULL,
  -- 026: image generation settings
  image_model             text        DEFAULT 'black-forest-labs/flux-schnell',
  image_style_preset      text        DEFAULT 'editorial-minimal',
  image_prompt_template   text,
  image_backend           text        DEFAULT 'replicate'
                                      CHECK (image_backend IN ('replicate','openai','pillo','mock')),
  -- 032: brand discovery URLs
  discovery_urls          text[]      DEFAULT '{}',
  -- timestamps
  created_at              timestamptz DEFAULT now(),
  updated_at              timestamptz DEFAULT now()
);

DROP TRIGGER IF EXISTS brands_updated_at ON brands;
CREATE TRIGGER brands_updated_at
  BEFORE UPDATE ON brands
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── users (extends Supabase Auth) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id    uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  role        user_role   NOT NULL DEFAULT 'viewer',
  email       text        NOT NULL,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_brand_id ON users(brand_id);

-- ── research_runs ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS research_runs (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  status           run_status  NOT NULL DEFAULT 'running',
  started_at       timestamptz DEFAULT now(),
  completed_at     timestamptz,
  sources_scanned  int         DEFAULT 0,
  items_found      int         DEFAULT 0,
  retriever_stats  jsonb       DEFAULT '{}',
  error_log        text
);

CREATE INDEX IF NOT EXISTS idx_research_runs_brand_status ON research_runs(brand_id, status);

-- ── research_items ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS research_items (
  id              uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid           NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  run_id          uuid           REFERENCES research_runs(id) ON DELETE SET NULL,
  url             text           NOT NULL,
  title           text,
  summary         text,
  source_name     text,
  source_type     source_type    NOT NULL,
  retriever_type  retriever_type NOT NULL,
  raw_content     text,
  metadata        jsonb          DEFAULT '{}',
  embedding       vector(1536),
  status          item_status    NOT NULL DEFAULT 'new',
  created_at      timestamptz    DEFAULT now(),
  CONSTRAINT uq_research_items_brand_url UNIQUE (brand_id, url)
);

CREATE INDEX IF NOT EXISTS idx_research_items_brand_status_created
  ON research_items(brand_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_items_embedding
  ON research_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_research_items_brand_created_desc
  ON research_items(brand_id, created_at DESC);

-- ── scores ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
  id                  uuid  PRIMARY KEY DEFAULT gen_random_uuid(),
  research_item_id    uuid  NOT NULL UNIQUE REFERENCES research_items(id) ON DELETE CASCADE,
  applicability       float NOT NULL CHECK (applicability BETWEEN 0 AND 10),
  credibility         float NOT NULL CHECK (credibility BETWEEN 0 AND 10),
  alignment           float NOT NULL CHECK (alignment BETWEEN 0 AND 10),
  trend_prediction    float NOT NULL CHECK (trend_prediction BETWEEN 0 AND 10),
  italy_relevance     float NOT NULL CHECK (italy_relevance BETWEEN 0 AND 10),
  feedback_bonus      float DEFAULT 0,
  final_score         float GENERATED ALWAYS AS (
    (applicability + credibility + alignment + trend_prediction + italy_relevance) / 5.0 + feedback_bonus
  ) STORED,
  model_used             text,
  scoring_prompt_version int,
  created_at             timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scores_final_score ON scores(final_score DESC);

-- ── content_drafts ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_drafts (
  id                uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid         NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  research_item_id  uuid         REFERENCES research_items(id) ON DELETE SET NULL,
  content_type      content_type NOT NULL,
  platform          platform     NOT NULL,
  title             text,
  body              text,
  media_urls        text[]       DEFAULT '{}',
  version           int          DEFAULT 1,
  parent_draft_id   uuid         REFERENCES content_drafts(id) ON DELETE SET NULL,
  status            draft_status NOT NULL DEFAULT 'draft',
  god_mode_result   jsonb,
  seo_score         int          CHECK (seo_score IS NULL OR (seo_score BETWEEN 0 AND 100)),
  scheduled_at      timestamptz,
  published_at      timestamptz,
  published_url     text,
  -- 029: metadata for Postiz integration
  metadata          jsonb        NOT NULL DEFAULT '{}',
  created_at        timestamptz  DEFAULT now(),
  updated_at        timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_drafts_brand_status_platform
  ON content_drafts(brand_id, status, platform);
CREATE INDEX IF NOT EXISTS idx_content_drafts_research_item
  ON content_drafts(research_item_id) WHERE research_item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_drafts_parent_id
  ON content_drafts(parent_draft_id) WHERE parent_draft_id IS NOT NULL;

DROP TRIGGER IF EXISTS content_drafts_updated_at ON content_drafts;
CREATE TRIGGER content_drafts_updated_at
  BEFORE UPDATE ON content_drafts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── god_mode_reviews ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS god_mode_reviews (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id              uuid        NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
  advocate_feedback     text,
  advocate_score        float,
  factcheck_feedback    text,
  factcheck_issues      jsonb,
  creative_feedback     text,
  creative_suggestions  jsonb,
  synthesis_result      text,
  final_verdict         god_verdict NOT NULL,
  model_config          jsonb,
  created_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_god_mode_reviews_draft_id ON god_mode_reviews(draft_id);

-- ── newsletters ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS newsletters (
  id                  uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid              NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  title               text              NOT NULL,
  edition_number      int               NOT NULL,
  slot_sistema_id     uuid              REFERENCES content_drafts(id) ON DELETE SET NULL,
  slot_strumento_id   uuid              REFERENCES content_drafts(id) ON DELETE SET NULL,
  slot_mossa_id       uuid              REFERENCES content_drafts(id) ON DELETE SET NULL,
  html_body           text,
  status              newsletter_status NOT NULL DEFAULT 'draft',
  scheduled_at        timestamptz,
  sent_at             timestamptz,
  recipients_count    int,
  open_rate           float,
  click_rate          float,
  unsubscribe_count   int,
  -- 034: layout type
  layout_type         text              CHECK (layout_type IN ('digest','single_story','announcement')),
  -- 035: A/B subject line variants
  subject_variant_a   text,
  subject_variant_b   text,
  -- 036: provider campaign link + A/B winner
  provider_campaign_id text,
  ab_winner           text              CHECK (ab_winner IN ('a','b')),
  created_at          timestamptz       DEFAULT now(),
  updated_at          timestamptz       DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_newsletters_brand_status ON newsletters(brand_id, status);

DROP TRIGGER IF EXISTS newsletters_updated_at ON newsletters;
CREATE TRIGGER newsletters_updated_at
  BEFORE UPDATE ON newsletters
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── newsletter_candidates ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS newsletter_candidates (
  id                uuid      PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id     uuid      NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  slot_type         slot_type NOT NULL,
  research_item_id  uuid      NOT NULL REFERENCES research_items(id) ON DELETE CASCADE,
  score             float,
  selected          boolean   DEFAULT false,
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_newsletter_candidates_newsletter
  ON newsletter_candidates(newsletter_id, slot_type);

-- ── campaigns ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
  id            uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid            NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name          text            NOT NULL,
  draft_ids     uuid[]          DEFAULT '{}',
  platforms     text[]          DEFAULT '{}',
  scheduled_at  timestamptz,
  status        campaign_status NOT NULL DEFAULT 'draft',
  results       jsonb,
  created_at    timestamptz     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_brand_status ON campaigns(brand_id, status);

-- ── calendar_events ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar_events (
  id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid         NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id        uuid         REFERENCES content_drafts(id) ON DELETE SET NULL,
  campaign_id     uuid         REFERENCES campaigns(id) ON DELETE SET NULL,
  event_type      event_type   NOT NULL,
  title           text         NOT NULL,
  scheduled_date  date         NOT NULL,
  scheduled_time  time,
  status          event_status NOT NULL DEFAULT 'planned',
  color           text,
  created_at      timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_brand_date
  ON calendar_events(brand_id, scheduled_date);

-- ── api_costs ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_costs (
  id             uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id       uuid          NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_name     text          NOT NULL,
  model          text          NOT NULL,
  operation      text          NOT NULL,
  tokens_input   int           DEFAULT 0,
  tokens_output  int           DEFAULT 0,
  cost_usd       decimal(10,6) NOT NULL,
  latency_ms     int,
  created_at     timestamptz   DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_costs_brand_created ON api_costs(brand_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_agent_model   ON api_costs(agent_name, model);
CREATE INDEX IF NOT EXISTS idx_api_costs_brand_agent_created
  ON api_costs(brand_id, agent_name, created_at DESC);

-- ── writing_lab_sessions ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS writing_lab_sessions (
  id                uuid       PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid       NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  topic             text       NOT NULL,
  content_type      text       NOT NULL,
  rounds_completed  int        DEFAULT 0,
  max_rounds        int        DEFAULT 50,
  current_champion  text,
  champion_version  int,
  hook_types_tried  jsonb      DEFAULT '[]',
  user_votes        jsonb      DEFAULT '{}',
  status            lab_status NOT NULL DEFAULT 'active',
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_writing_lab_sessions_brand_status
  ON writing_lab_sessions(brand_id, status);

DROP TRIGGER IF EXISTS writing_lab_sessions_updated_at ON writing_lab_sessions;
CREATE TRIGGER writing_lab_sessions_updated_at
  BEFORE UPDATE ON writing_lab_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── writing_lab_rounds ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS writing_lab_rounds (
  id                    uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            uuid         NOT NULL REFERENCES writing_lab_sessions(id) ON DELETE CASCADE,
  round_number          int          NOT NULL,
  champion_text         text         NOT NULL,
  challenger_text       text         NOT NULL,
  hook_type_champion    text,
  hook_type_challenger  text,
  winner                round_winner,
  user_feedback         text,
  created_at            timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_writing_lab_rounds_session
  ON writing_lab_rounds(session_id, round_number);

-- ── revenue_deals ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS revenue_deals (
  id            uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid            NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  partner_name  text            NOT NULL,
  deal_type     deal_type       NOT NULL,
  amount        decimal(10,2)   NOT NULL,
  currency      text            DEFAULT 'EUR',
  recurrence    recurrence_type NOT NULL,
  start_date    date            NOT NULL,
  end_date      date,
  status        deal_status     NOT NULL DEFAULT 'proposal',
  notes         text,
  created_at    timestamptz     DEFAULT now(),
  updated_at    timestamptz     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revenue_deals_brand_status ON revenue_deals(brand_id, status);

DROP TRIGGER IF EXISTS revenue_deals_updated_at ON revenue_deals;
CREATE TRIGGER revenue_deals_updated_at
  BEFORE UPDATE ON revenue_deals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── pipeline_health ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_health (
  id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid          NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_name      text          NOT NULL,
  uptime_pct      float,
  avg_latency_ms  int,
  errors_today    int           DEFAULT 0,
  queue_size      int           DEFAULT 0,
  last_heartbeat  timestamptz,
  status          health_status NOT NULL DEFAULT 'healthy',
  -- 013: LLM metadata
  current_model   text,
  fallback_model  text,
  engine          text          NOT NULL DEFAULT 'unknown',
  last_latency_ms int,
  last_seen       timestamptz,
  created_at      timestamptz   DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_agent
  ON pipeline_health(brand_id, agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_status
  ON pipeline_health(brand_id, status, last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_agent_latest
  ON pipeline_health(brand_id, agent_name, created_at DESC);

-- ── feedback ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
  id                uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid            NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id          uuid            REFERENCES content_drafts(id) ON DELETE SET NULL,
  research_item_id  uuid            REFERENCES research_items(id) ON DELETE SET NULL,
  feedback_type     feedback_type   NOT NULL,
  value             text,
  source            feedback_source NOT NULL,
  created_at        timestamptz     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_brand_draft ON feedback(brand_id, draft_id);
CREATE INDEX IF NOT EXISTS idx_feedback_research_item
  ON feedback(research_item_id) WHERE research_item_id IS NOT NULL;

-- ── audit_trail (from 002) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_trail (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id    text,
  action      text        NOT NULL,
  platform    text        DEFAULT '',
  status      text        NOT NULL DEFAULT 'success',
  details     jsonb       DEFAULT '{}',
  error       text,
  timestamp   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_trail_brand_action
  ON audit_trail(brand_id, action, timestamp DESC);


-- ============================================================================
-- §5  AGENT SYSTEM (from 005 + 018 additions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_configs (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_key           text        NOT NULL,
  agent_name          text        NOT NULL,
  identity            text        NOT NULL DEFAULT '',
  task_type_override  text,
  is_active           boolean     NOT NULL DEFAULT true,
  version             int         NOT NULL DEFAULT 1,
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),
  UNIQUE(brand_id, agent_key)
);

CREATE TABLE IF NOT EXISTS agent_config_versions (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  config_id   uuid        NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
  identity    text        NOT NULL,
  version     int         NOT NULL,
  changed_by  text,
  created_at  timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_skills (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id              uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  skill_name            text        NOT NULL,
  target_agent          text        NOT NULL,
  priority              text        NOT NULL DEFAULT 'medium'
                                    CHECK (priority IN ('high', 'medium', 'low')),
  instructions          text        NOT NULL DEFAULT '',
  tags                  text[]      DEFAULT '{}',
  is_active             boolean     NOT NULL DEFAULT true,
  -- 018: procedural memory tracking
  success_count         int         NOT NULL DEFAULT 0,
  failure_count         int         NOT NULL DEFAULT 0,
  last_optimized_at     timestamptz,
  optimization_history  jsonb       NOT NULL DEFAULT '[]',
  created_at            timestamptz DEFAULT now(),
  updated_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_configs_brand ON agent_configs(brand_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_agent_skills_brand  ON agent_skills(brand_id, target_agent);


-- ============================================================================
-- §6  FEEDBACK LOOP & SOCIAL METRICS (from 008)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_metrics (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id     uuid        NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
  platform     text        NOT NULL,
  impressions  int         NOT NULL DEFAULT 0,
  clicks       int         NOT NULL DEFAULT 0,
  likes        int         NOT NULL DEFAULT 0,
  shares       int         NOT NULL DEFAULT 0,
  comments     int         NOT NULL DEFAULT 0,
  saves        int         NOT NULL DEFAULT 0,
  recorded_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE(draft_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_social_metrics_draft    ON social_metrics(draft_id);
CREATE INDEX IF NOT EXISTS idx_social_metrics_recorded ON social_metrics(recorded_at);

CREATE TABLE IF NOT EXISTS feedback_loop_audit (
  id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid          NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  previous_bonus  decimal(5,2)  NOT NULL DEFAULT 0,
  new_bonus       decimal(5,2)  NOT NULL DEFAULT 0,
  metrics_used    jsonb         NOT NULL DEFAULT '{}',
  score_delta     decimal(5,2)  GENERATED ALWAYS AS (new_bonus - previous_bonus) STORED,
  executed_at     timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_loop_audit_brand    ON feedback_loop_audit(brand_id);
CREATE INDEX IF NOT EXISTS idx_feedback_loop_audit_executed ON feedback_loop_audit(executed_at);

-- Engagement summary function
CREATE OR REPLACE FUNCTION get_draft_engagement_summary(p_draft_id uuid)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public AS $$
  SELECT COALESCE(
    jsonb_build_object(
      'impressions', SUM(impressions),
      'clicks',      SUM(clicks),
      'likes',       SUM(likes),
      'shares',      SUM(shares),
      'comments',    SUM(comments),
      'saves',       SUM(saves)
    ),
    '{}'::jsonb
  )
  FROM social_metrics
  WHERE draft_id = p_draft_id
$$;

-- ── rate_limit_counters (from 004) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rate_limit_counters (
  key          text        NOT NULL PRIMARY KEY,
  count        int         NOT NULL DEFAULT 1,
  window_start timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_window ON rate_limit_counters(window_start);


-- ============================================================================
-- §7  HUMANIZER (from 011)
-- ============================================================================

CREATE TABLE IF NOT EXISTS humanizer_performance (
  id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id            uuid          NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
  brand_id            uuid          NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  ai_patterns_found   int           NOT NULL DEFAULT 0,
  remaining_ai_tells  int           NOT NULL DEFAULT 0,
  engagement_score    decimal(5,2),
  platform            text          NOT NULL,
  model_used          text,
  created_at          timestamptz   DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_humanizer_brand    ON humanizer_performance(brand_id);
CREATE INDEX IF NOT EXISTS idx_humanizer_draft    ON humanizer_performance(draft_id);
CREATE INDEX IF NOT EXISTS idx_humanizer_platform ON humanizer_performance(platform);


-- ============================================================================
-- §8  LLM FALLBACK MONITORING (from 012)
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_fallback_log (
  id              uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid    NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  context         text    NOT NULL,
  action          text    NOT NULL,
  primary_model   text    NOT NULL,
  fallback_reason text    NOT NULL,
  is_emergency    boolean NOT NULL DEFAULT false,
  created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_fallback_brand      ON llm_fallback_log(brand_id);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_created_at  ON llm_fallback_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_emergency   ON llm_fallback_log(is_emergency, created_at DESC);


-- ============================================================================
-- §9  MULTI-BRAND MEMBERSHIP (from 017)
-- ============================================================================

CREATE TABLE IF NOT EXISTS brand_members (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id   uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  role       text        NOT NULL DEFAULT 'owner'
               CHECK (role IN ('owner', 'admin', 'member')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, brand_id)
);

CREATE INDEX IF NOT EXISTS idx_brand_members_user       ON brand_members(user_id);
CREATE INDEX IF NOT EXISTS idx_brand_members_brand      ON brand_members(brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_members_user_brand ON brand_members(user_id, brand_id);

-- Primary membership check — used by ALL RLS policies
CREATE OR REPLACE FUNCTION user_has_brand(p_brand_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM brand_members
    WHERE user_id = auth.uid() AND brand_id = p_brand_id
  )
$$;

-- Backward-compat: returns oldest brand for current user
CREATE OR REPLACE FUNCTION auth_user_brand_id()
RETURNS uuid
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp AS $$
  SELECT brand_id FROM brand_members
  WHERE user_id = auth.uid()
  ORDER BY created_at LIMIT 1
$$;

-- Role check (reads from users table)
CREATE OR REPLACE FUNCTION auth_user_role()
RETURNS user_role
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT role FROM users WHERE id = auth.uid()
$$;

-- Research items status counts
CREATE OR REPLACE FUNCTION research_items_status_counts(p_brand_id uuid)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT COALESCE(jsonb_object_agg(status, cnt), '{}'::jsonb)
  FROM (
    SELECT status::text, count(*) AS cnt
    FROM research_items WHERE brand_id = p_brand_id
    GROUP BY status
  ) sub
$$;

-- Create brand RPC
CREATE OR REPLACE FUNCTION create_brand_with_owner(
  p_name text, p_slug text, p_topics text[] DEFAULT '{}'
)
RETURNS json
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_brand_id uuid; v_user_id uuid := auth.uid(); v_email text;
BEGIN
  IF v_user_id IS NULL THEN RAISE EXCEPTION 'Not authenticated'; END IF;
  IF p_name IS NULL OR trim(p_name) = '' THEN RAISE EXCEPTION 'name is required'; END IF;
  IF p_slug IS NULL OR trim(p_slug) = '' THEN RAISE EXCEPTION 'slug is required'; END IF;
  IF EXISTS (SELECT 1 FROM brands WHERE slug = p_slug) THEN RAISE EXCEPTION 'slug_taken'; END IF;

  SELECT email INTO v_email FROM auth.users WHERE id = v_user_id;

  INSERT INTO brands (name, slug, topics)
  VALUES (trim(p_name), p_slug, COALESCE(p_topics, '{}'))
  RETURNING id INTO v_brand_id;

  INSERT INTO brand_members (user_id, brand_id, role)
  VALUES (v_user_id, v_brand_id, 'owner')
  ON CONFLICT (user_id, brand_id) DO NOTHING;

  INSERT INTO users (id, brand_id, role, email)
  VALUES (v_user_id, v_brand_id, 'owner'::user_role, v_email)
  ON CONFLICT (id) DO NOTHING;

  RETURN json_build_object('id', v_brand_id, 'name', trim(p_name), 'slug', p_slug);
END;
$$;


-- ============================================================================
-- §10  MEMORY LAYER (from 018)
-- ============================================================================

-- ── memory_hot: session scratchpad ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_hot (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  session_id   text        NOT NULL,
  key          text        NOT NULL,
  value        jsonb       NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
  UNIQUE (brand_id, session_id, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_hot_brand_session ON memory_hot(brand_id, session_id);
CREATE INDEX IF NOT EXISTS idx_memory_hot_expires       ON memory_hot(expires_at);
CREATE INDEX IF NOT EXISTS idx_memory_hot_brand_key     ON memory_hot(brand_id, key);

-- ── memory_semantic: warm semantic store ───────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_semantic (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  kind             text        NOT NULL,
  statement        text        NOT NULL,
  embedding        vector(1536),
  tier             memory_tier NOT NULL DEFAULT 'standard',
  importance       numeric(3,2) NOT NULL DEFAULT 0.50 CHECK (importance BETWEEN 0 AND 1),
  source_kind      text,
  source_id        uuid,
  asserted_at      timestamptz NOT NULL DEFAULT now(),
  expires_at       timestamptz,
  supersedes_id    uuid        REFERENCES memory_semantic(id) ON DELETE SET NULL,
  last_retrieved   timestamptz,
  retrieval_hits   int         NOT NULL DEFAULT 0,
  metadata         jsonb       NOT NULL DEFAULT '{}',
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_kind    ON memory_semantic(brand_id, kind);
CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_tier    ON memory_semantic(brand_id, tier);
CREATE INDEX IF NOT EXISTS idx_memory_semantic_expires       ON memory_semantic(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_semantic_supersedes    ON memory_semantic(supersedes_id) WHERE supersedes_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_expires ON memory_semantic(brand_id, expires_at DESC) WHERE expires_at IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_memory_semantic_embedding') THEN
    CREATE INDEX idx_memory_semantic_embedding
      ON memory_semantic USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
  END IF;
END; $$;

CREATE OR REPLACE FUNCTION set_memory_semantic_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS memory_semantic_updated_at ON memory_semantic;
CREATE TRIGGER memory_semantic_updated_at
  BEFORE UPDATE ON memory_semantic
  FOR EACH ROW EXECUTE FUNCTION set_memory_semantic_updated_at();

-- ── memory_events ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_events (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  event_kind   text        NOT NULL,
  subject_kind text,
  subject_id   uuid,
  summary      text        NOT NULL,
  payload      jsonb       NOT NULL DEFAULT '{}',
  occurred_at  timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz DEFAULT (now() + interval '90 days')
);

CREATE INDEX IF NOT EXISTS idx_memory_events_brand_kind ON memory_events(brand_id, event_kind, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_events_expires    ON memory_events(expires_at) WHERE expires_at IS NOT NULL;

-- ── memory_archive: cold storage, monthly partitioned ──────────────────────
CREATE TABLE IF NOT EXISTS memory_archive (
  id            uuid        NOT NULL DEFAULT gen_random_uuid(),
  brand_id      uuid        NOT NULL,
  origin_table  text        NOT NULL,
  origin_id     uuid        NOT NULL,
  payload       jsonb       NOT NULL,
  archived_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, archived_at)
) PARTITION BY RANGE (archived_at);

-- Bootstrap current-month partition
DO $$ DECLARE
  v_start date := date_trunc('month', now())::date;
  v_end   date := (date_trunc('month', now()) + interval '1 month')::date;
  v_name  text := 'memory_archive_' || to_char(now(), 'YYYYMM');
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = v_name AND relkind = 'r') THEN
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS public.%I PARTITION OF memory_archive FOR VALUES FROM (%L) TO (%L)',
      v_name, v_start, v_end
    );
  END IF;
END; $$;

-- Memory helper functions
CREATE OR REPLACE FUNCTION memory_touch(p_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
DECLARE v_tier memory_tier; v_ttl interval;
BEGIN
  SELECT tier INTO v_tier FROM memory_semantic WHERE id = p_id;
  IF NOT FOUND THEN RETURN; END IF;
  v_ttl := memory_ttl(v_tier);
  UPDATE memory_semantic SET
    retrieval_hits = retrieval_hits + 1,
    last_retrieved = now(),
    expires_at = CASE WHEN v_ttl IS NULL THEN NULL ELSE now() + v_ttl END
  WHERE id = p_id;
END; $$;

CREATE OR REPLACE FUNCTION memory_search(
  p_brand_id uuid, p_embedding vector(1536), p_kind text DEFAULT NULL, p_limit int DEFAULT 10
)
RETURNS TABLE (id uuid, kind text, statement text, tier memory_tier, importance numeric, similarity float, age_days float, score float)
LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT ms.id, ms.kind, ms.statement, ms.tier, ms.importance,
    ROUND((1 - (ms.embedding <=> p_embedding))::numeric, 4)::float,
    ROUND(EXTRACT(EPOCH FROM (now() - ms.asserted_at)) / 86400.0, 1)::float,
    ROUND((
      0.60 * (1 - (ms.embedding <=> p_embedding)) +
      0.25 * EXP(-0.02 * EXTRACT(EPOCH FROM (now() - ms.asserted_at)) / 86400.0) +
      0.15 * ms.importance::float
    )::numeric, 4)::float
  FROM memory_semantic ms
  WHERE ms.brand_id = p_brand_id
    AND ms.embedding IS NOT NULL
    AND (ms.expires_at IS NULL OR ms.expires_at > now())
    AND (p_kind IS NULL OR ms.kind = p_kind)
  ORDER BY 8 DESC LIMIT p_limit
$$;


-- ============================================================================
-- §11  BRAND ASSETS & IMAGE GENERATION (from 025, 026)
-- ============================================================================

CREATE TABLE IF NOT EXISTS brand_assets (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  kind          text        NOT NULL CHECK (kind IN (
                  'logo_primary','logo_mono','logo_favicon',
                  'palette','font_specimen','design_system_pdf',
                  'example_newsletter','example_post','example_carousel',
                  'watermark','other'
                )),
  label         text,
  storage_path  text        NOT NULL,
  mime_type     text        NOT NULL,
  bytes         bigint      NOT NULL,
  width_px      int,
  height_px     int,
  palette_hex   text[],
  metadata      jsonb       NOT NULL DEFAULT '{}',
  uploaded_by   uuid        REFERENCES auth.users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_assets_brand_kind ON brand_assets(brand_id, kind);
CREATE UNIQUE INDEX IF NOT EXISTS uq_brand_assets_single_primary_logo
  ON brand_assets(brand_id) WHERE kind = 'logo_primary';

CREATE OR REPLACE FUNCTION touch_brand_assets_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_brand_assets_touch ON brand_assets;
CREATE TRIGGER trg_brand_assets_touch
  BEFORE UPDATE ON brand_assets FOR EACH ROW EXECUTE FUNCTION touch_brand_assets_updated_at();

CREATE TABLE IF NOT EXISTS image_generations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id        uuid        REFERENCES content_drafts(id) ON DELETE SET NULL,
  backend         text        NOT NULL,
  model_id        text        NOT NULL,
  prompt          text        NOT NULL,
  negative_prompt text,
  seed            bigint,
  status          text        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','running','succeeded','failed')),
  storage_path    text,
  public_url      text,
  width_px        int,
  height_px       int,
  cost_usd        numeric(10,4),
  error           text,
  started_at      timestamptz,
  finished_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imggen_brand_draft    ON image_generations(brand_id, draft_id);
CREATE INDEX IF NOT EXISTS idx_imggen_status_created ON image_generations(status, created_at DESC);


-- ============================================================================
-- §12  FEATURE FLAGS (from 031)
-- ============================================================================

CREATE TABLE IF NOT EXISTS feature_flags (
  id         uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id   uuid    NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  key        text    NOT NULL,
  value      boolean NOT NULL DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE (brand_id, key)
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_brand_key ON feature_flags(brand_id, key);

CREATE OR REPLACE FUNCTION touch_feature_flags_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_feature_flags_touch ON feature_flags;
CREATE TRIGGER trg_feature_flags_touch
  BEFORE UPDATE ON feature_flags FOR EACH ROW EXECUTE FUNCTION touch_feature_flags_updated_at();


-- ============================================================================
-- §13  BRAND INTEGRATIONS — consolidated credentials store (032 + 033)
-- ============================================================================
-- Replaces both brand_integrations AND brand_service_credentials.
-- Per-key storage: (brand_id, provider, key_name) → encrypted_value.

CREATE TABLE IF NOT EXISTS brand_integrations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  provider        text        NOT NULL,
  key_name        text        NOT NULL,
  encrypted_value text        NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, provider, key_name)
);

CREATE INDEX IF NOT EXISTS idx_brand_integrations_brand  ON brand_integrations(brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_integrations_lookup ON brand_integrations(brand_id, provider);

CREATE OR REPLACE FUNCTION touch_brand_integrations_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_brand_integrations_touch ON brand_integrations;
CREATE TRIGGER trg_brand_integrations_touch
  BEFORE UPDATE ON brand_integrations FOR EACH ROW EXECUTE FUNCTION touch_brand_integrations_updated_at();


-- ============================================================================
-- §14  EMAIL & NEWSLETTER EXTENSIONS (033, 036)
-- ============================================================================

-- ── email_provider_config (from 033_email_provider_config) ─────────────────
CREATE TABLE IF NOT EXISTS email_provider_config (
  brand_id        uuid    PRIMARY KEY REFERENCES brands(id) ON DELETE CASCADE,
  provider        text    NOT NULL CHECK (provider IN ('brevo','mailchimp','resend')),
  api_key         text,
  sender_name     text,
  sender_email    text,
  list_id         text,
  webhook_secret  text,
  ab_split_pct    int     CHECK (ab_split_pct BETWEEN 5 AND 50),
  ab_wait_hours   int     CHECK (ab_wait_hours BETWEEN 1 AND 168),
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

-- ── newsletter_events (from 036_newsletter_ab_and_events) ──────────────────
CREATE TABLE IF NOT EXISTS newsletter_events (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id  uuid        NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  event_type     text        NOT NULL CHECK (event_type IN ('delivered','opened','clicked','bounced','unsubscribed')),
  email          text,
  occurred_at    timestamptz NOT NULL DEFAULT now(),
  metadata       jsonb,
  created_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_newsletter_events_newsletter ON newsletter_events(newsletter_id);
CREATE INDEX IF NOT EXISTS idx_newsletter_events_occurred   ON newsletter_events(occurred_at);


-- ============================================================================
-- §15  DEEP RESEARCH (from 035, 037 retriever type)
-- ============================================================================

CREATE TABLE IF NOT EXISTS deep_research_jobs (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  topic        text        NOT NULL,
  depth        int         NOT NULL CHECK (depth BETWEEN 1 AND 5),
  status       text        NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','running','completed','failed')),
  external_id  text,
  result       jsonb,
  sources      jsonb,
  error        text,
  started_at   timestamptz,
  completed_at timestamptz,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deep_research_brand_status ON deep_research_jobs(brand_id, status);

CREATE OR REPLACE FUNCTION touch_deep_research_jobs_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_deep_research_jobs_touch ON deep_research_jobs;
CREATE TRIGGER trg_deep_research_jobs_touch
  BEFORE UPDATE ON deep_research_jobs FOR EACH ROW EXECUTE FUNCTION touch_deep_research_jobs_updated_at();


-- ============================================================================
-- §16  COMPETITOR WATCH (from 036)
-- ============================================================================

CREATE TABLE IF NOT EXISTS competitor_snapshots (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  url         text        NOT NULL,
  title       text,
  content     text,
  metadata    jsonb,
  status      text        NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','running','completed','failed')),
  error       text,
  captured_at timestamptz,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_competitor_brand_url    ON competitor_snapshots(brand_id, url);
CREATE INDEX IF NOT EXISTS idx_competitor_brand_recent ON competitor_snapshots(brand_id, created_at DESC);


-- ============================================================================
-- §17  NOTIFICATION EVENTS (from 037)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notification_events (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid        REFERENCES brands(id) ON DELETE CASCADE,  -- nullable for system events
  event_type  text        NOT NULL,
  severity    text        NOT NULL CHECK (severity IN ('info','success','warning','error')),
  title       text        NOT NULL,
  detail      jsonb,
  entity_type text,
  entity_id   text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_events_brand   ON notification_events(brand_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_created ON notification_events(created_at);


-- ============================================================================
-- §18  VIDEO SYSTEM (from 038, 039, 040)
-- ============================================================================

CREATE TABLE IF NOT EXISTS video_templates (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid        REFERENCES brands(id) ON DELETE CASCADE,  -- NULL = system template
  name             text        NOT NULL,
  slug             text        NOT NULL,
  description      text,
  composition_path text        NOT NULL,
  props_schema     jsonb       NOT NULL DEFAULT '{}',
  thumbnail_url    text,
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now(),
  UNIQUE (brand_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_video_templates_brand ON video_templates(brand_id);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_video_templates_updated_at') THEN
    CREATE TRIGGER trg_video_templates_updated_at
      BEFORE UPDATE ON video_templates FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END; $$;

CREATE TABLE IF NOT EXISTS videos (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  template_id   uuid        REFERENCES video_templates(id) ON DELETE SET NULL,
  title         text        NOT NULL,
  status        text        NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','rendering','completed','failed')),
  render_props  jsonb       DEFAULT '{}',
  output_url    text,
  storage_path  text,
  duration_secs numeric,
  error         text,
  -- 040: HeyGen support
  kind          text        NOT NULL DEFAULT 'hyperframes'
                CHECK (kind IN ('hyperframes','heygen')),
  heygen_video_id text,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_videos_brand_status  ON videos(brand_id, status);
CREATE INDEX IF NOT EXISTS idx_videos_brand_created ON videos(brand_id, created_at DESC);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_videos_updated_at') THEN
    CREATE TRIGGER trg_videos_updated_at
      BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END; $$;

-- ── heygen_usage (from 040) ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS heygen_usage (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  year_month   text        NOT NULL,
  minutes_used numeric     NOT NULL DEFAULT 0,
  updated_at   timestamptz DEFAULT now(),
  UNIQUE (brand_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_heygen_usage_brand ON heygen_usage(brand_id);


-- ============================================================================
-- §19  BREVO (from 033_brevo_foundation, 041_brevo_campaigns)
-- ============================================================================

CREATE TABLE IF NOT EXISTS brevo_contacts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  brevo_id        bigint,
  email           text        NOT NULL,
  first_name      text,
  last_name       text,
  attributes      jsonb       DEFAULT '{}',
  list_ids        int[]       DEFAULT '{}',
  is_blocklisted  boolean     DEFAULT false,
  synced_at       timestamptz,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),
  UNIQUE (brand_id, email)
);

CREATE INDEX IF NOT EXISTS idx_brevo_contacts_brand  ON brevo_contacts(brand_id);
CREATE INDEX IF NOT EXISTS idx_brevo_contacts_email  ON brevo_contacts(email);
CREATE INDEX IF NOT EXISTS idx_brevo_contacts_synced ON brevo_contacts(synced_at);

CREATE OR REPLACE FUNCTION touch_brevo_contacts_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_brevo_contacts_touch ON brevo_contacts;
CREATE TRIGGER trg_brevo_contacts_touch
  BEFORE UPDATE ON brevo_contacts FOR EACH ROW EXECUTE FUNCTION touch_brevo_contacts_updated_at();

CREATE TABLE IF NOT EXISTS brevo_campaigns (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid        NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id            uuid        REFERENCES content_drafts(id) ON DELETE SET NULL,
  brevo_campaign_id   bigint,
  name                text        NOT NULL,
  subject             text,
  status              text        NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','scheduled','sent','archived')),
  scheduled_at        timestamptz,
  sent_at             timestamptz,
  recipient_count     int,
  metrics             jsonb,
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brevo_campaigns_brand    ON brevo_campaigns(brand_id);
CREATE INDEX IF NOT EXISTS idx_brevo_campaigns_brevo_id ON brevo_campaigns(brevo_campaign_id) WHERE brevo_campaign_id IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_brevo_campaigns_updated_at') THEN
    CREATE TRIGGER trg_brevo_campaigns_updated_at
      BEFORE UPDATE ON brevo_campaigns FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END; $$;


-- ============================================================================
-- §20  EMAIL AUTOMATIONS (from 042)
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_automations (
  id                  uuid   PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid   NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name                text   NOT NULL,
  template_key        text   NOT NULL CHECK (template_key IN ('welcome','nurture','win-back')),
  status              text   NOT NULL DEFAULT 'inactive'
                      CHECK (status IN ('active','inactive')),
  brevo_workflow_id   bigint,
  steps               jsonb  DEFAULT '[]',
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),
  UNIQUE (brand_id, template_key)
);

CREATE INDEX IF NOT EXISTS idx_email_automations_brand ON email_automations(brand_id);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_email_automations_updated_at') THEN
    CREATE TRIGGER trg_email_automations_updated_at
      BEFORE UPDATE ON email_automations FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END; $$;

-- ── LLM provider metrics (from 034) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS llm_provider_metrics (
  id                uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid           NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  provider          text           NOT NULL,
  model             text           NOT NULL,
  task_type         text,
  prompt_tokens     int,
  completion_tokens int,
  latency_ms        int,
  cost_usd          numeric(12,8),
  is_fallback       boolean        DEFAULT false,
  error             text,
  ts                timestamptz    DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_metrics_brand_ts       ON llm_provider_metrics(brand_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_llm_metrics_brand_provider ON llm_provider_metrics(brand_id, provider);


-- ============================================================================
-- §21  VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW v_content_pipeline AS
SELECT ri.id AS research_item_id, ri.brand_id, ri.title AS research_title,
  ri.url, ri.source_name, ri.source_type, ri.retriever_type,
  ri.status AS research_status, ri.created_at AS discovered_at,
  s.final_score, s.applicability, s.credibility, s.alignment,
  s.trend_prediction, s.italy_relevance, s.feedback_bonus,
  s.model_used AS scoring_model,
  cd.id AS draft_id, cd.content_type, cd.platform,
  cd.title AS draft_title, cd.status AS draft_status,
  cd.version AS draft_version, cd.seo_score,
  cd.scheduled_at, cd.published_at, cd.published_url
FROM research_items ri
LEFT JOIN scores s ON s.research_item_id = ri.id
LEFT JOIN content_drafts cd ON cd.research_item_id = ri.id;

CREATE OR REPLACE VIEW v_daily_costs AS
SELECT brand_id, date_trunc('day', created_at)::date AS day,
  agent_name, model,
  COUNT(*) AS api_calls,
  SUM(tokens_input) AS total_tokens_in,
  SUM(tokens_output) AS total_tokens_out,
  SUM(cost_usd) AS total_cost_usd,
  AVG(latency_ms)::int AS avg_latency_ms
FROM api_costs
GROUP BY brand_id, date_trunc('day', created_at), agent_name, model;

CREATE OR REPLACE VIEW v_newsletter_performance AS
SELECT n.brand_id, n.id AS newsletter_id, n.title, n.edition_number,
  n.status, n.recipients_count, n.open_rate, n.click_rate,
  n.unsubscribe_count, n.scheduled_at, n.sent_at,
  COUNT(nc.id) AS candidates_count,
  COUNT(nc.id) FILTER (WHERE nc.selected) AS selected_count
FROM newsletters n
LEFT JOIN newsletter_candidates nc ON nc.newsletter_id = n.id
GROUP BY n.id, n.brand_id, n.title, n.edition_number, n.status,
  n.recipients_count, n.open_rate, n.click_rate,
  n.unsubscribe_count, n.scheduled_at, n.sent_at;

CREATE OR REPLACE VIEW v_daily_fallback_stats AS
SELECT DATE(created_at AT TIME ZONE 'UTC') AS date, brand_id, context,
  COUNT(*) AS total_fallbacks,
  COUNT(*) FILTER (WHERE is_emergency) AS emergency_fallbacks,
  COUNT(*) FILTER (WHERE NOT is_emergency) AS normal_fallbacks,
  ARRAY_AGG(DISTINCT primary_model) AS failed_models,
  MAX(created_at) AS last_fallback_at
FROM llm_fallback_log
WHERE created_at >= CURRENT_DATE - interval '30 days'
GROUP BY DATE(created_at AT TIME ZONE 'UTC'), brand_id, context;

CREATE OR REPLACE VIEW vw_memory_episodic AS
  SELECT 'llm_call'::text AS event_kind, brand_id, agent_name AS subject_kind,
    NULL::uuid AS subject_id,
    format('%s %s | tokens=%s cost=$%s', agent_name, operation,
      COALESCE(tokens_input,0)+COALESCE(tokens_output,0),
      ROUND(COALESCE(cost_usd,0)::numeric,4)) AS summary,
    jsonb_build_object('model',model,'latency_ms',latency_ms,
      'tokens_in',tokens_input,'tokens_out',tokens_output,'cost_usd',cost_usd) AS payload,
    created_at AS occurred_at
  FROM api_costs
UNION ALL
  SELECT action::text, brand_id, 'content_draft'::text,
    CASE WHEN draft_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
         THEN draft_id::uuid ELSE NULL::uuid END,
    format('%s -> %s on %s', action, status, platform),
    jsonb_build_object('draft_id',draft_id) || COALESCE(details,'{}'),
    timestamp
  FROM audit_trail WHERE draft_id IS NOT NULL
UNION ALL
  SELECT 'feedback_bonus'::text, brand_id, 'scores'::text, NULL::uuid,
    format('bonus %s -> %s (d%s)', previous_bonus, new_bonus, score_delta),
    jsonb_build_object('previous_bonus',previous_bonus,'new_bonus',new_bonus,
      'score_delta',score_delta,'metrics_used',metrics_used),
    executed_at
  FROM feedback_loop_audit
UNION ALL
  SELECT 'writing_lab_vote'::text, wls.brand_id, 'writing_lab_session'::text, wls.id,
    format('round %s winner: %s', wlr.round_number, COALESCE(wlr.winner::text,'undecided')),
    jsonb_build_object('round',wlr.round_number,'winner',wlr.winner::text,'feedback',wlr.user_feedback),
    wlr.created_at
  FROM writing_lab_rounds wlr
  JOIN writing_lab_sessions wls ON wls.id = wlr.session_id
UNION ALL
  SELECT event_kind, brand_id, subject_kind, subject_id, summary, payload, occurred_at
  FROM memory_events WHERE expires_at IS NULL OR expires_at > now();


-- ============================================================================
-- §22  ROW LEVEL SECURITY
-- ============================================================================
-- All policies use user_has_brand() from §9 (migration 017 pattern).

-- Enable RLS on all tables
ALTER TABLE brands                ENABLE ROW LEVEL SECURITY;
ALTER TABLE users                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_runs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores                ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_drafts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE god_mode_reviews      ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletters           ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns             ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_costs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE writing_lab_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE writing_lab_rounds    ENABLE ROW LEVEL SECURITY;
ALTER TABLE revenue_deals         ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_health       ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback              ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_trail           ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_configs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_skills          ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_metrics        ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_loop_audit   ENABLE ROW LEVEL SECURITY;
ALTER TABLE humanizer_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_fallback_log      ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_members         ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_hot            ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_semantic       ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_events         ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_counters   ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_assets          ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_generations     ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_flags         ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_integrations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_provider_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_events     ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_research_jobs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_snapshots  ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_templates       ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos                ENABLE ROW LEVEL SECURITY;
ALTER TABLE heygen_usage          ENABLE ROW LEVEL SECURITY;
ALTER TABLE brevo_contacts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE brevo_campaigns       ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_automations     ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_provider_metrics  ENABLE ROW LEVEL SECURITY;

-- ── Macro: brand-scoped SELECT/INSERT/UPDATE/DELETE ────────────────────────
-- Applied to tables with direct brand_id FK.

-- Helper: drop+create pattern for idempotency
-- brands (special: user_has_brand(id) not brand_id)
DROP POLICY IF EXISTS "brands_select" ON brands;
CREATE POLICY "brands_select" ON brands FOR SELECT USING (user_has_brand(id));
DROP POLICY IF EXISTS "brands_update" ON brands;
CREATE POLICY "brands_update" ON brands FOR UPDATE USING (user_has_brand(id) AND auth_user_role() = 'owner')
  WITH CHECK (user_has_brand(id) AND auth_user_role() = 'owner');

-- users
DROP POLICY IF EXISTS "users_select" ON users;
CREATE POLICY "users_select" ON users FOR SELECT USING (user_has_brand(brand_id));
DROP POLICY IF EXISTS "users_insert" ON users;
CREATE POLICY "users_insert" ON users FOR INSERT WITH CHECK (user_has_brand(brand_id) AND auth_user_role() = 'owner');
DROP POLICY IF EXISTS "users_update" ON users;
CREATE POLICY "users_update" ON users FOR UPDATE USING (user_has_brand(brand_id) AND auth_user_role() = 'owner');
DROP POLICY IF EXISTS "users_delete" ON users;
CREATE POLICY "users_delete" ON users FOR DELETE USING (user_has_brand(brand_id) AND auth_user_role() = 'owner');

-- brand_members (special: user_id = auth.uid())
DROP POLICY IF EXISTS "brand_members_select" ON brand_members;
CREATE POLICY "brand_members_select" ON brand_members FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS "brand_members_insert" ON brand_members;
CREATE POLICY "brand_members_insert" ON brand_members FOR INSERT WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "brand_members_delete" ON brand_members;
CREATE POLICY "brand_members_delete" ON brand_members FOR DELETE USING (user_id = auth.uid() OR auth_user_role() = 'owner');

-- Generic brand-scoped: SELECT + INSERT(editor+) + UPDATE(editor+) + DELETE(owner)
-- research_runs, research_items, content_drafts, newsletters, campaigns, calendar_events,
-- writing_lab_sessions, revenue_deals, pipeline_health, feedback, audit_trail, agent_configs, agent_skills

DO $$ DECLARE t text;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'research_runs','research_items','content_drafts','newsletters',
    'campaigns','calendar_events','writing_lab_sessions','revenue_deals',
    'agent_configs','agent_skills'
  ]) LOOP
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_select" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_select" ON %1$s FOR SELECT USING (user_has_brand(brand_id))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_insert" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_insert" ON %1$s FOR INSERT WITH CHECK (user_has_brand(brand_id) AND auth_user_role() IN (''owner'',''editor''))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_update" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_update" ON %1$s FOR UPDATE USING (user_has_brand(brand_id) AND auth_user_role() IN (''owner'',''editor''))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_delete" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_delete" ON %1$s FOR DELETE USING (user_has_brand(brand_id) AND auth_user_role() = ''owner'')', t);
  END LOOP;
END; $$;

-- Append-only tables (select + insert only)
DO $$ DECLARE t text;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'api_costs','feedback','audit_trail','humanizer_performance',
    'llm_fallback_log','feedback_loop_audit'
  ]) LOOP
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_select" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_select" ON %1$s FOR SELECT USING (user_has_brand(brand_id))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_insert" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_insert" ON %1$s FOR INSERT WITH CHECK (user_has_brand(brand_id))', t);
  END LOOP;
END; $$;

-- social_metrics: no direct brand_id — joins through content_drafts
DROP POLICY IF EXISTS "social_metrics_select" ON social_metrics;
CREATE POLICY "social_metrics_select" ON social_metrics
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = social_metrics.draft_id
        AND user_has_brand(cd.brand_id)
    )
  );
DROP POLICY IF EXISTS "social_metrics_insert" ON social_metrics;
CREATE POLICY "social_metrics_insert" ON social_metrics
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = draft_id
        AND user_has_brand(cd.brand_id)
    )
  );

-- Pipeline health (select + insert + update, no delete)
DROP POLICY IF EXISTS "pipeline_health_select" ON pipeline_health;
CREATE POLICY "pipeline_health_select" ON pipeline_health FOR SELECT USING (user_has_brand(brand_id));
DROP POLICY IF EXISTS "pipeline_health_insert" ON pipeline_health;
CREATE POLICY "pipeline_health_insert" ON pipeline_health FOR INSERT WITH CHECK (user_has_brand(brand_id));
DROP POLICY IF EXISTS "pipeline_health_update" ON pipeline_health;
CREATE POLICY "pipeline_health_update" ON pipeline_health FOR UPDATE USING (user_has_brand(brand_id));

-- Indirect tables (via FK join)
-- scores (via research_items.brand_id)
DROP POLICY IF EXISTS "scores_select" ON scores;
CREATE POLICY "scores_select" ON scores FOR SELECT USING (
  EXISTS (SELECT 1 FROM research_items ri WHERE ri.id = scores.research_item_id AND user_has_brand(ri.brand_id)));
DROP POLICY IF EXISTS "scores_insert" ON scores;
CREATE POLICY "scores_insert" ON scores FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM research_items ri WHERE ri.id = scores.research_item_id AND user_has_brand(ri.brand_id))
  AND auth_user_role() IN ('owner','editor'));

-- god_mode_reviews (via content_drafts.brand_id)
DROP POLICY IF EXISTS "god_mode_reviews_select" ON god_mode_reviews;
CREATE POLICY "god_mode_reviews_select" ON god_mode_reviews FOR SELECT USING (
  EXISTS (SELECT 1 FROM content_drafts cd WHERE cd.id = god_mode_reviews.draft_id AND user_has_brand(cd.brand_id)));

-- newsletter_candidates (via newsletters.brand_id)
DROP POLICY IF EXISTS "newsletter_candidates_select" ON newsletter_candidates;
CREATE POLICY "newsletter_candidates_select" ON newsletter_candidates FOR SELECT USING (
  EXISTS (SELECT 1 FROM newsletters n WHERE n.id = newsletter_candidates.newsletter_id AND user_has_brand(n.brand_id)));

-- writing_lab_rounds (via writing_lab_sessions.brand_id)
DROP POLICY IF EXISTS "writing_lab_rounds_select" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_select" ON writing_lab_rounds FOR SELECT USING (
  EXISTS (SELECT 1 FROM writing_lab_sessions wls WHERE wls.id = writing_lab_rounds.session_id AND user_has_brand(wls.brand_id)));
DROP POLICY IF EXISTS "writing_lab_rounds_insert" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_insert" ON writing_lab_rounds FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM writing_lab_sessions wls WHERE wls.id = writing_lab_rounds.session_id AND user_has_brand(wls.brand_id))
  AND auth_user_role() IN ('owner','editor'));

-- Full CRUD via user_has_brand for newer tables
DO $$ DECLARE t text;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'memory_hot','memory_semantic','memory_events',
    'brand_assets','feature_flags','brand_integrations',
    'deep_research_jobs','competitor_snapshots',
    'video_templates','videos','heygen_usage',
    'brevo_contacts','brevo_campaigns','email_automations',
    'llm_provider_metrics'
  ]) LOOP
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_select" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_select" ON %1$s FOR SELECT USING (user_has_brand(brand_id))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_insert" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_insert" ON %1$s FOR INSERT WITH CHECK (user_has_brand(brand_id))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_update" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_update" ON %1$s FOR UPDATE USING (user_has_brand(brand_id))', t);
    EXECUTE format('DROP POLICY IF EXISTS "%1$s_delete" ON %1$s', t);
    EXECUTE format('CREATE POLICY "%1$s_delete" ON %1$s FOR DELETE USING (user_has_brand(brand_id))', t);
  END LOOP;
END; $$;

-- image_generations (select + insert + update only)
DROP POLICY IF EXISTS "imggen_select" ON image_generations;
CREATE POLICY "imggen_select" ON image_generations FOR SELECT USING (user_has_brand(brand_id));
DROP POLICY IF EXISTS "imggen_insert" ON image_generations;
CREATE POLICY "imggen_insert" ON image_generations FOR INSERT WITH CHECK (user_has_brand(brand_id));
DROP POLICY IF EXISTS "imggen_update" ON image_generations;
CREATE POLICY "imggen_update" ON image_generations FOR UPDATE USING (user_has_brand(brand_id));

-- email_provider_config (via brand_members join)
DROP POLICY IF EXISTS "epc_select" ON email_provider_config;
CREATE POLICY "epc_select" ON email_provider_config FOR SELECT USING (user_has_brand(brand_id));
DROP POLICY IF EXISTS "epc_insert" ON email_provider_config;
CREATE POLICY "epc_insert" ON email_provider_config FOR INSERT WITH CHECK (user_has_brand(brand_id));
DROP POLICY IF EXISTS "epc_update" ON email_provider_config;
CREATE POLICY "epc_update" ON email_provider_config FOR UPDATE USING (user_has_brand(brand_id));

-- newsletter_events (via newsletters FK)
DROP POLICY IF EXISTS "ne_select" ON newsletter_events;
CREATE POLICY "ne_select" ON newsletter_events FOR SELECT USING (
  EXISTS (SELECT 1 FROM newsletters n JOIN brand_members bm ON bm.brand_id = n.brand_id
    WHERE n.id = newsletter_events.newsletter_id AND bm.user_id = auth.uid()));

-- notification_events (nullable brand_id — system events visible to all)
DROP POLICY IF EXISTS "notif_select" ON notification_events;
CREATE POLICY "notif_select" ON notification_events FOR SELECT USING (
  brand_id IS NULL OR user_has_brand(brand_id));

-- video_templates (NULL brand_id = system-wide, readable by all authenticated)
DROP POLICY IF EXISTS "video_templates_select" ON video_templates;
CREATE POLICY "video_templates_select" ON video_templates FOR SELECT USING (
  brand_id IS NULL OR user_has_brand(brand_id));


-- ============================================================================
-- §23  STORAGE BUCKETS
-- ============================================================================

INSERT INTO storage.buckets (id, name, public) VALUES ('brand-assets','brand-assets', false)
  ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS brand_assets_storage_read ON storage.objects;
CREATE POLICY brand_assets_storage_read ON storage.objects FOR SELECT USING (
  bucket_id = 'brand-assets' AND user_has_brand((split_part(name, '/', 1))::uuid));
DROP POLICY IF EXISTS brand_assets_storage_write ON storage.objects;
CREATE POLICY brand_assets_storage_write ON storage.objects FOR INSERT WITH CHECK (
  bucket_id = 'brand-assets' AND user_has_brand((split_part(name, '/', 1))::uuid));
DROP POLICY IF EXISTS brand_assets_storage_delete ON storage.objects;
CREATE POLICY brand_assets_storage_delete ON storage.objects FOR DELETE USING (
  bucket_id = 'brand-assets' AND user_has_brand((split_part(name, '/', 1))::uuid));

INSERT INTO storage.buckets (id, name, public) VALUES ('generated-images','generated-images', false)
  ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS generated_images_read ON storage.objects;
CREATE POLICY generated_images_read ON storage.objects FOR SELECT USING (
  bucket_id = 'generated-images' AND user_has_brand((split_part(name, '/', 1))::uuid));
DROP POLICY IF EXISTS generated_images_write ON storage.objects;
CREATE POLICY generated_images_write ON storage.objects FOR INSERT WITH CHECK (
  bucket_id = 'generated-images' AND user_has_brand((split_part(name, '/', 1))::uuid));


-- ============================================================================
-- §24  CRON JOBS (pg_cron)
-- ============================================================================

DO $$ BEGIN
  -- Memory TTL sweep: 03:30 UTC daily
  BEGIN PERFORM cron.unschedule('memory-ttl-sweep'); EXCEPTION WHEN OTHERS THEN NULL; END;
  PERFORM cron.schedule('memory-ttl-sweep', '30 3 * * *',
    'DELETE FROM public.memory_hot WHERE expires_at < now();'
    '  INSERT INTO public.memory_archive (brand_id, origin_table, origin_id, payload)'
    '  SELECT brand_id, ''memory_semantic'', id, row_to_json(memory_semantic)::jsonb'
    '  FROM public.memory_semantic WHERE expires_at IS NOT NULL AND expires_at < now();'
    '  DELETE FROM public.memory_semantic WHERE expires_at IS NOT NULL AND expires_at < now();'
    '  DELETE FROM public.memory_events WHERE expires_at IS NOT NULL AND expires_at < now();'
  );

  -- Monthly archive partition: 1st of month 00:05 UTC
  BEGIN PERFORM cron.unschedule('memory-archive-partition'); EXCEPTION WHEN OTHERS THEN NULL; END;
  PERFORM cron.schedule('memory-archive-partition', '5 0 1 * *', $cmd$
    DO $inner$ DECLARE
      v_start date := date_trunc('month', now() + interval '1 month')::date;
      v_end   date := date_trunc('month', now() + interval '2 months')::date;
      v_name  text := 'memory_archive_' || to_char(now() + interval '1 month', 'YYYYMM');
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = v_name AND relkind = 'r') THEN
        EXECUTE format('CREATE TABLE IF NOT EXISTS public.%I PARTITION OF public.memory_archive FOR VALUES FROM (%L) TO (%L)', v_name, v_start, v_end);
      END IF;
    END; $inner$
  $cmd$);
END; $$;


-- ============================================================================
-- §25  SEED DATA
-- ============================================================================

-- Agent config seeds (per existing brand)
INSERT INTO agent_configs (brand_id, agent_key, agent_name, identity)
SELECT b.id, a.agent_key, a.agent_name, a.default_identity
FROM brands b
CROSS JOIN (VALUES
  ('writer',        'Writer',           'Sei il Writer del brand.'),
  ('editor',        'Editor',           'Sei l''Editor del brand.'),
  ('adapter',       'Adapter',          'Sei l''Adapter multi-piattaforma.'),
  ('god_advocate',  'GOD Advocate',     'Sei l''Avvocato del Diavolo del GOD System.'),
  ('god_factcheck', 'GOD Fact-Checker', 'Sei il Fact-Checker del GOD System.'),
  ('god_creative',  'GOD Creative',     'Sei il Direttore Creativo del GOD System.'),
  ('god_synthesis', 'GOD Synthesis',    'Sei il Sintetizzatore del GOD System.')
) AS a(agent_key, agent_name, default_identity)
ON CONFLICT (brand_id, agent_key) DO NOTHING;

-- Video template seeds
INSERT INTO video_templates (brand_id, name, slug, description, composition_path, props_schema)
VALUES
  (NULL, 'Weekly Recap', 'weekly-recap', 'Animated summary of the week''s top content',
   'compositions/weekly-recap', '{"type":"object","properties":{"brand_name":{"type":"string"},"accent_color":{"type":"string","default":"#6366f1"},"week_start":{"type":"string","description":"YYYY-MM-DD"}}}'),
  (NULL, 'Carousel -> Reel', 'carousel-to-reel', 'Convert a carousel into an animated vertical reel',
   'compositions/carousel-to-reel', '{"type":"object","properties":{"brand_name":{"type":"string"},"accent_color":{"type":"string","default":"#6366f1"},"slides":{"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"body":{"type":"string"}}}}}}')
ON CONFLICT DO NOTHING;


-- ============================================================================
-- §26  GRANTS
-- ============================================================================

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

GRANT SELECT, INSERT, DELETE ON brand_members TO authenticated;
GRANT SELECT ON vw_memory_episodic TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON memory_hot TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON memory_semantic TO authenticated;
GRANT SELECT, INSERT, DELETE ON memory_events TO authenticated;

REVOKE ALL ON FUNCTION create_brand_with_owner(text, text, text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION create_brand_with_owner(text, text, text[]) TO authenticated;
GRANT EXECUTE ON FUNCTION research_items_status_counts(uuid) TO anon, authenticated, service_role;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
