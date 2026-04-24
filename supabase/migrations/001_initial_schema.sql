-- ============================================================================
-- AI Content Engine - Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Database: Supabase (PostgreSQL 15+)
-- Description: Complete schema for multi-brand AI content automation platform
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXTENSIONS
-- ----------------------------------------------------------------------------

-- Ensure extensions schema exists for Supabase/Postgres
CREATE SCHEMA IF NOT EXISTS extensions;

-- Vector similarity search for semantic retrieval
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

-- Scheduled jobs
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Ensure extension types (vector, etc.) are resolvable without schema prefix
SET search_path = public, extensions;

-- ----------------------------------------------------------------------------
-- 2. CUSTOM ENUM TYPES
-- ----------------------------------------------------------------------------

-- User roles within a brand
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE user_role AS ENUM ('owner', 'editor', 'viewer');
  END IF;
END $$;

-- Research run execution status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'run_status') THEN
    CREATE TYPE run_status AS ENUM ('running', 'completed', 'failed');
  END IF;
END $$;

-- Source types for discovered content
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type') THEN
    CREATE TYPE source_type AS ENUM ('rss', 'search', 'youtube', 'scrape');
  END IF;
END $$;

-- Retriever strategies used during research
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'retriever_type') THEN
    CREATE TYPE retriever_type AS ENUM (
      'semantic', 'practitioner', 'trusted_source', 'keyword', 'trend'
    );
  END IF;
END $$;

-- Research item lifecycle status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_status') THEN
    CREATE TYPE item_status AS ENUM ('new', 'scored', 'approved', 'rejected', 'archived');
  END IF;
END $$;

-- Content draft types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_type') THEN
    CREATE TYPE content_type AS ENUM (
      'post', 'blog', 'newsletter_section', 'carousel', 'video_script', 'thread'
    );
  END IF;
END $$;

-- Publishing platforms
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'platform') THEN
    CREATE TYPE platform AS ENUM (
      'linkedin', 'instagram', 'facebook', 'x', 'tiktok', 'blog', 'newsletter'
    );
  END IF;
END $$;

-- Draft workflow status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'draft_status') THEN
    CREATE TYPE draft_status AS ENUM (
      'draft', 'in_review', 'god_mode', 'approved', 'scheduled', 'published', 'archived'
    );
  END IF;
END $$;

-- GOD mode review verdict
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'god_verdict') THEN
    CREATE TYPE god_verdict AS ENUM ('pass', 'needs_revision', 'reject');
  END IF;
END $$;

-- Newsletter lifecycle status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newsletter_status') THEN
    CREATE TYPE newsletter_status AS ENUM (
      'draft', 'in_review', 'approved', 'scheduled', 'sent'
    );
  END IF;
END $$;

-- Newsletter slot types (3-slot structure)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'slot_type') THEN
    CREATE TYPE slot_type AS ENUM ('sistema', 'strumento_lampo', 'mossa');
  END IF;
END $$;

-- Campaign distribution status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_status') THEN
    CREATE TYPE campaign_status AS ENUM (
      'draft', 'scheduled', 'publishing', 'completed', 'failed'
    );
  END IF;
END $$;

-- Calendar event types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type') THEN
    CREATE TYPE event_type AS ENUM ('newsletter', 'social', 'blog_video', 'sponsorship');
  END IF;
END $$;

-- Calendar event status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_status') THEN
    CREATE TYPE event_status AS ENUM ('planned', 'confirmed', 'published');
  END IF;
END $$;

-- Writing Lab session status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lab_status') THEN
    CREATE TYPE lab_status AS ENUM ('active', 'completed', 'paused');
  END IF;
END $$;

-- A/B round winner
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'round_winner') THEN
    CREATE TYPE round_winner AS ENUM ('champion', 'challenger', 'draw');
  END IF;
END $$;

-- Revenue deal types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_type') THEN
    CREATE TYPE deal_type AS ENUM (
      'sponsorship', 'affiliate', 'newsletter_feature', 'product'
    );
  END IF;
END $$;

-- Deal recurrence
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recurrence_type') THEN
    CREATE TYPE recurrence_type AS ENUM ('one_time', 'monthly', 'quarterly');
  END IF;
END $$;

-- Deal lifecycle status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_status') THEN
    CREATE TYPE deal_status AS ENUM (
      'proposal', 'negotiation', 'confirmed', 'active', 'completed', 'cancelled'
    );
  END IF;
END $$;

-- Pipeline agent health status
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'health_status') THEN
    CREATE TYPE health_status AS ENUM ('healthy', 'degraded', 'down');
  END IF;
END $$;

-- Feedback types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_type') THEN
    CREATE TYPE feedback_type AS ENUM ('like', 'dislike', 'top_pick', 'comment');
  END IF;
END $$;

-- Feedback origin
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'feedback_source') THEN
    CREATE TYPE feedback_source AS ENUM ('manual', 'writing_lab', 'analytics');
  END IF;
END $$;


-- ----------------------------------------------------------------------------
-- 3. HELPER FUNCTIONS
-- ----------------------------------------------------------------------------

-- Auto-update updated_at timestamp on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4.1 brands - Multi-brand configuration hub
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS brands (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text NOT NULL,
  slug            text NOT NULL UNIQUE,
  topics          text[] DEFAULT '{}',
  tone_of_voice   jsonb DEFAULT '{}',
  scoring_weights jsonb DEFAULT '{}',
  rss_sources     jsonb DEFAULT '[]',
  social_accounts jsonb DEFAULT '{}',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE brands IS 'Multi-brand configuration. Each brand is an independent editorial project.';
COMMENT ON COLUMN brands.topics IS 'Array of topic/niche keywords the brand monitors.';
COMMENT ON COLUMN brands.tone_of_voice IS 'JSON config for writing style, register, personality.';
COMMENT ON COLUMN brands.scoring_weights IS 'Custom weights for the 5-axis scoring formula.';
COMMENT ON COLUMN brands.rss_sources IS 'Array of RSS feed URLs and metadata to monitor.';
COMMENT ON COLUMN brands.social_accounts IS 'Connected social accounts with platform and tokens.';

DROP TRIGGER IF EXISTS brands_updated_at ON brands;
CREATE TRIGGER brands_updated_at
  BEFORE UPDATE ON brands
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4.2 users - Authenticated users (extends Supabase Auth)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id    uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  role        user_role NOT NULL DEFAULT 'viewer',
  email       text NOT NULL,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz DEFAULT now()
);

COMMENT ON TABLE users IS 'User profiles extending Supabase Auth. Each user belongs to exactly one brand.';
COMMENT ON COLUMN users.role IS 'Access level: owner (full), editor (create/edit), viewer (read-only).';

CREATE INDEX IF NOT EXISTS idx_users_brand_id ON users(brand_id);


-- ----------------------------------------------------------------------------
-- 4.3 research_runs - Research pipeline execution sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS research_runs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  status           run_status NOT NULL DEFAULT 'running',
  started_at       timestamptz DEFAULT now(),
  completed_at     timestamptz,
  sources_scanned  int DEFAULT 0,
  items_found      int DEFAULT 0,
  retriever_stats  jsonb DEFAULT '{}',
  error_log        text
);

COMMENT ON TABLE research_runs IS 'Tracks each execution of the research pipeline with statistics and outcomes.';
COMMENT ON COLUMN research_runs.retriever_stats IS 'Per-retriever breakdown: items found, latency, errors.';

CREATE INDEX IF NOT EXISTS idx_research_runs_brand_status ON research_runs(brand_id, status);


-- ----------------------------------------------------------------------------
-- 4.4 research_items - Content discovered by research pipeline
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS research_items (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  run_id          uuid REFERENCES research_runs(id) ON DELETE SET NULL,
  url             text NOT NULL,
  title           text,
  summary         text,
  source_name     text,
  source_type     source_type NOT NULL,
  retriever_type  retriever_type NOT NULL,
  raw_content     text,
  metadata        jsonb DEFAULT '{}',
  embedding       vector(1536),
  status          item_status NOT NULL DEFAULT 'new',
  created_at      timestamptz DEFAULT now(),

  -- Prevent duplicate URLs within the same brand
  CONSTRAINT uq_research_items_brand_url UNIQUE (brand_id, url)
);

COMMENT ON TABLE research_items IS 'Content items discovered by research retrievers. Core entity of the discovery pipeline.';
COMMENT ON COLUMN research_items.embedding IS '1536-dim vector from text-embedding-3-small for semantic similarity search.';
COMMENT ON COLUMN research_items.retriever_type IS 'Strategy that found this item: semantic, practitioner, trusted_source, keyword, trend.';

CREATE INDEX IF NOT EXISTS idx_research_items_brand_status_created
  ON research_items(brand_id, status, created_at DESC);

-- IVFFlat index for vector similarity search (cosine distance)
-- Note: requires at least ~1000 rows to be effective; use sequential scan for smaller datasets
CREATE INDEX IF NOT EXISTS idx_research_items_embedding
  ON research_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- ----------------------------------------------------------------------------
-- 4.5 scores - Multi-axis content scoring
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scores (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  research_item_id       uuid NOT NULL UNIQUE REFERENCES research_items(id) ON DELETE CASCADE,
  applicability          float NOT NULL CHECK (applicability >= 0 AND applicability <= 10),
  credibility            float NOT NULL CHECK (credibility >= 0 AND credibility <= 10),
  alignment              float NOT NULL CHECK (alignment >= 0 AND alignment <= 10),
  trend_prediction       float NOT NULL CHECK (trend_prediction >= 0 AND trend_prediction <= 10),
  italy_relevance        float NOT NULL CHECK (italy_relevance >= 0 AND italy_relevance <= 10),
  feedback_bonus         float DEFAULT 0,
  final_score            float GENERATED ALWAYS AS (
    (applicability + credibility + alignment + trend_prediction + italy_relevance) / 5.0 + feedback_bonus
  ) STORED,
  model_used             text,
  scoring_prompt_version int,
  created_at             timestamptz DEFAULT now()
);

COMMENT ON TABLE scores IS 'Multi-axis scoring for research items. 1:1 relationship with research_items.';
COMMENT ON COLUMN scores.final_score IS 'Computed: average of 5 axes + feedback_bonus. Range roughly 0-12.';
COMMENT ON COLUMN scores.feedback_bonus IS 'Bonus points from human feedback (can be negative).';

CREATE INDEX IF NOT EXISTS idx_scores_final_score ON scores(final_score DESC);


-- ----------------------------------------------------------------------------
-- 4.6 content_drafts - Generated content drafts
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_drafts (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  research_item_id  uuid REFERENCES research_items(id) ON DELETE SET NULL,
  content_type      content_type NOT NULL,
  platform          platform NOT NULL,
  title             text,
  body              text,
  media_urls        text[] DEFAULT '{}',
  version           int DEFAULT 1,
  parent_draft_id   uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  status            draft_status NOT NULL DEFAULT 'draft',
  god_mode_result   jsonb,
  seo_score         int CHECK (seo_score IS NULL OR (seo_score >= 0 AND seo_score <= 100)),
  scheduled_at      timestamptz,
  published_at      timestamptz,
  published_url     text,
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now()
);

COMMENT ON TABLE content_drafts IS 'Content drafts with full versioning and approval workflow. Supports self-referencing for version chains.';
COMMENT ON COLUMN content_drafts.parent_draft_id IS 'Previous version of this draft (self-referencing for version chain).';
COMMENT ON COLUMN content_drafts.god_mode_result IS 'Summary of GOD mode review outcome.';

CREATE INDEX IF NOT EXISTS idx_content_drafts_brand_status_platform
  ON content_drafts(brand_id, status, platform);

CREATE INDEX IF NOT EXISTS idx_content_drafts_research_item
  ON content_drafts(research_item_id) WHERE research_item_id IS NOT NULL;

DROP TRIGGER IF EXISTS content_drafts_updated_at ON content_drafts;
CREATE TRIGGER content_drafts_updated_at
  BEFORE UPDATE ON content_drafts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4.7 god_mode_reviews - GOD system review results (3-agent debate)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS god_mode_reviews (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id              uuid NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
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

COMMENT ON TABLE god_mode_reviews IS 'Three-agent review system: Advocate, FactChecker, Creative with final synthesis.';
COMMENT ON COLUMN god_mode_reviews.factcheck_issues IS 'Array of factual issues: [{claim, status, source}].';
COMMENT ON COLUMN god_mode_reviews.creative_suggestions IS 'Structured creative improvements: [{area, suggestion, priority}].';

CREATE INDEX IF NOT EXISTS idx_god_mode_reviews_draft_id ON god_mode_reviews(draft_id);


-- ----------------------------------------------------------------------------
-- 4.8 newsletters - Composed newsletters (3-slot structure)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS newsletters (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id           uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  title              text NOT NULL,
  edition_number     int NOT NULL,
  slot_sistema_id    uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  slot_strumento_id  uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  slot_mossa_id      uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  html_body          text,
  status             newsletter_status NOT NULL DEFAULT 'draft',
  scheduled_at       timestamptz,
  sent_at            timestamptz,
  recipients_count   int,
  open_rate          float,
  click_rate         float,
  unsubscribe_count  int,
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now()
);

COMMENT ON TABLE newsletters IS 'Newsletter editions with 3 themed slots: Sistema, Strumento Lampo, Mossa.';
COMMENT ON COLUMN newsletters.edition_number IS 'Sequential edition number for the brand.';

CREATE INDEX IF NOT EXISTS idx_newsletters_brand_status ON newsletters(brand_id, status);

DROP TRIGGER IF EXISTS newsletters_updated_at ON newsletters;
CREATE TRIGGER newsletters_updated_at
  BEFORE UPDATE ON newsletters
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4.9 newsletter_candidates - Candidate items for each newsletter slot
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS newsletter_candidates (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id     uuid NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
  slot_type         slot_type NOT NULL,
  research_item_id  uuid NOT NULL REFERENCES research_items(id) ON DELETE CASCADE,
  score             float,
  selected          boolean DEFAULT false,
  created_at        timestamptz DEFAULT now()
);

COMMENT ON TABLE newsletter_candidates IS 'Candidate research items proposed for each newsletter slot. One is selected per slot.';

CREATE INDEX IF NOT EXISTS idx_newsletter_candidates_newsletter
  ON newsletter_candidates(newsletter_id, slot_type);


-- ----------------------------------------------------------------------------
-- 4.10 campaigns - Distribution campaigns
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name              text NOT NULL,
  draft_ids         uuid[] DEFAULT '{}',
  platforms         text[] DEFAULT '{}',
  scheduled_at      timestamptz,
  status            campaign_status NOT NULL DEFAULT 'draft',
  results           jsonb,
  created_at        timestamptz DEFAULT now()
);

-- Ensure draft_ids exists if table already existed (idempotency polish)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='campaigns' AND column_name='draft_ids') THEN
    ALTER TABLE campaigns ADD COLUMN draft_ids uuid[] DEFAULT '{}';
  END IF;
END $$;

COMMENT ON TABLE campaigns IS 'Multi-platform distribution campaigns grouping multiple content drafts.';
COMMENT ON COLUMN campaigns.draft_ids IS 'Array of content_draft UUIDs included in this campaign.';

CREATE INDEX IF NOT EXISTS idx_campaigns_brand_status ON campaigns(brand_id, status);


-- ----------------------------------------------------------------------------
-- 4.11 calendar_events - Editorial calendar
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_events (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id          uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  campaign_id       uuid REFERENCES campaigns(id) ON DELETE SET NULL,
  event_type        event_type NOT NULL,
  title             text NOT NULL,
  scheduled_date    date NOT NULL,
  scheduled_time    time,
  status            event_status NOT NULL DEFAULT 'planned',
  color             text,
  created_at        timestamptz DEFAULT now()
);

-- Ensure draft_id exists if table already existed (idempotency polish)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='calendar_events' AND column_name='draft_id') THEN
    ALTER TABLE calendar_events ADD COLUMN draft_id uuid REFERENCES content_drafts(id) ON DELETE SET NULL;
  END IF;
END $$;

COMMENT ON TABLE calendar_events IS 'Editorial calendar linking drafts and campaigns to specific dates.';

CREATE INDEX IF NOT EXISTS idx_calendar_events_brand_date
  ON calendar_events(brand_id, scheduled_date);


-- ----------------------------------------------------------------------------
-- 4.12 api_costs - API cost tracking
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_costs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id       uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_name     text NOT NULL,
  model          text NOT NULL,
  operation      text NOT NULL,
  tokens_input   int DEFAULT 0,
  tokens_output  int DEFAULT 0,
  cost_usd       decimal(10,6) NOT NULL,
  latency_ms     int,
  created_at     timestamptz DEFAULT now()
);

COMMENT ON TABLE api_costs IS 'Granular cost tracking for every API call (LLM, embedding, scraping).';
COMMENT ON COLUMN api_costs.agent_name IS 'Pipeline agent that made the call (e.g. scorer, writer, researcher).';

CREATE INDEX IF NOT EXISTS idx_api_costs_brand_created ON api_costs(brand_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_agent_model ON api_costs(agent_name, model);






-- ----------------------------------------------------------------------------
-- 4.14 writing_lab_sessions - Writing Lab A/B testing sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS writing_lab_sessions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  topic             text NOT NULL,
  content_type      text NOT NULL,
  rounds_completed  int DEFAULT 0,
  max_rounds        int DEFAULT 50,
  current_champion  text,
  champion_version  int,
  hook_types_tried  jsonb DEFAULT '[]',
  user_votes        jsonb DEFAULT '{}',
  status            lab_status NOT NULL DEFAULT 'active',
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now()
);

COMMENT ON TABLE writing_lab_sessions IS 'A/B testing sessions for copy optimization. Up to 50 rounds per session.';
COMMENT ON COLUMN writing_lab_sessions.hook_types_tried IS 'Array of hook types already tested in this session.';

CREATE INDEX IF NOT EXISTS idx_writing_lab_sessions_brand_status
  ON writing_lab_sessions(brand_id, status);

DROP TRIGGER IF EXISTS writing_lab_sessions_updated_at ON writing_lab_sessions;
CREATE TRIGGER writing_lab_sessions_updated_at
  BEFORE UPDATE ON writing_lab_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4.15 writing_lab_rounds - Individual A/B test rounds
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS writing_lab_rounds (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            uuid NOT NULL REFERENCES writing_lab_sessions(id) ON DELETE CASCADE,
  round_number          int NOT NULL,
  champion_text         text NOT NULL,
  challenger_text       text NOT NULL,
  hook_type_champion    text,
  hook_type_challenger  text,
  winner                round_winner,
  user_feedback         text,
  created_at            timestamptz DEFAULT now()
);

COMMENT ON TABLE writing_lab_rounds IS 'Single A/B comparison round between champion and challenger texts.';

CREATE INDEX IF NOT EXISTS idx_writing_lab_rounds_session
  ON writing_lab_rounds(session_id, round_number);


-- ----------------------------------------------------------------------------
-- 4.16 revenue_deals - Revenue deals and sponsorships
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS revenue_deals (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  partner_name  text NOT NULL,
  deal_type     deal_type NOT NULL,
  amount        decimal(10,2) NOT NULL,
  currency      text DEFAULT 'EUR',
  recurrence    recurrence_type NOT NULL,
  start_date    date NOT NULL,
  end_date      date,
  status        deal_status NOT NULL DEFAULT 'proposal',
  notes         text,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

COMMENT ON TABLE revenue_deals IS 'Revenue tracking: sponsorships, affiliates, newsletter features, product deals.';

CREATE INDEX IF NOT EXISTS idx_revenue_deals_brand_status ON revenue_deals(brand_id, status);

DROP TRIGGER IF EXISTS revenue_deals_updated_at ON revenue_deals;
CREATE TRIGGER revenue_deals_updated_at
  BEFORE UPDATE ON revenue_deals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4.17 pipeline_health - System health monitoring
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_health (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_name      text NOT NULL,
  uptime_pct      float,
  avg_latency_ms  int,
  errors_today    int DEFAULT 0,
  queue_size      int DEFAULT 0,
  last_heartbeat  timestamptz,
  status          health_status NOT NULL DEFAULT 'healthy',
  created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE pipeline_health IS 'Real-time health monitoring for each pipeline agent. Periodic heartbeat check.';

CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_agent
  ON pipeline_health(brand_id, agent_name, created_at DESC);


-- ----------------------------------------------------------------------------
-- 4.18 feedback - Human feedback on content
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id          uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  research_item_id  uuid REFERENCES research_items(id) ON DELETE SET NULL,
  feedback_type     feedback_type NOT NULL,
  value             text,
  source            feedback_source NOT NULL,
  created_at        timestamptz DEFAULT now()
);

-- Ensure draft_id exists if table already existed (idempotency polish)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='feedback' AND column_name='draft_id') THEN
    ALTER TABLE feedback ADD COLUMN draft_id uuid REFERENCES content_drafts(id) ON DELETE SET NULL;
  END IF;
END $$;

COMMENT ON TABLE feedback IS 'Explicit human feedback on content and research items. Feeds back into scoring bonus.';

CREATE INDEX IF NOT EXISTS idx_feedback_brand_draft ON feedback(brand_id, draft_id);
CREATE INDEX IF NOT EXISTS idx_feedback_research_item ON feedback(research_item_id)
  WHERE research_item_id IS NOT NULL;


-- ============================================================================
-- 5. VIEWS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5.1 v_content_pipeline - Full pipeline view (research -> score -> draft)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_content_pipeline AS
SELECT
  ri.id                AS research_item_id,
  ri.brand_id,
  ri.title             AS research_title,
  ri.url,
  ri.source_name,
  ri.source_type,
  ri.retriever_type,
  ri.status            AS research_status,
  ri.created_at        AS discovered_at,
  s.final_score,
  s.applicability,
  s.credibility,
  s.alignment,
  s.trend_prediction,
  s.italy_relevance,
  s.feedback_bonus,
  s.model_used         AS scoring_model,
  cd.id                AS draft_id,
  cd.content_type,
  cd.platform,
  cd.title             AS draft_title,
  cd.status            AS draft_status,
  cd.version           AS draft_version,
  cd.seo_score,
  cd.scheduled_at,
  cd.published_at,
  cd.published_url
FROM research_items ri
LEFT JOIN scores s ON s.research_item_id = ri.id
LEFT JOIN content_drafts cd ON cd.research_item_id = ri.id;

COMMENT ON VIEW v_content_pipeline IS 'End-to-end pipeline view joining research_items, scores, and content_drafts.';


-- ----------------------------------------------------------------------------
-- 5.2 v_daily_costs - Daily cost aggregation by agent and model
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_daily_costs AS
SELECT
  brand_id,
  date_trunc('day', created_at)::date AS day,
  agent_name,
  model,
  COUNT(*)                             AS api_calls,
  SUM(tokens_input)                    AS total_tokens_in,
  SUM(tokens_output)                   AS total_tokens_out,
  SUM(cost_usd)                        AS total_cost_usd,
  AVG(latency_ms)::int                 AS avg_latency_ms
FROM api_costs
GROUP BY brand_id, date_trunc('day', created_at), agent_name, model;

COMMENT ON VIEW v_daily_costs IS 'Daily cost aggregation broken down by agent and model for budget monitoring.';


-- ----------------------------------------------------------------------------
-- 5.3 v_newsletter_performance - Newsletter metrics with candidate stats
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_newsletter_performance AS
SELECT
  n.brand_id,
  n.id                  AS newsletter_id,
  n.title,
  n.edition_number,
  n.status,
  n.recipients_count,
  n.open_rate,
  n.click_rate,
  n.unsubscribe_count,
  n.scheduled_at,
  n.sent_at,
  COUNT(nc.id)                              AS candidates_count,
  COUNT(nc.id) FILTER (WHERE nc.selected)   AS selected_count
FROM newsletters n
LEFT JOIN newsletter_candidates nc ON nc.newsletter_id = n.id
GROUP BY n.id, n.brand_id, n.title, n.edition_number, n.status,
         n.recipients_count, n.open_rate, n.click_rate,
         n.unsubscribe_count, n.scheduled_at, n.sent_at;

COMMENT ON VIEW v_newsletter_performance IS 'Aggregated newsletter performance with candidate selection statistics.';


-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Helper: get the brand_id for the current authenticated user.
-- Redefined in migration 017 to support multi-brand membership; bootstrap
-- definition here references public.users (single-brand era) so RLS policies
-- in this migration compile cleanly on a fresh database.
CREATE OR REPLACE FUNCTION auth_user_brand_id()
RETURNS uuid AS $$
  SELECT brand_id FROM public.users WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Helper: get the role for the current authenticated user.
CREATE OR REPLACE FUNCTION auth_user_role()
RETURNS user_role AS $$
  SELECT role FROM public.users WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

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


-- ── brands ──────────────────────────────────────────────────────────────────

-- Users can see their own brand
DROP POLICY IF EXISTS "brands_select" ON brands;
CREATE POLICY "brands_select" ON brands
  FOR SELECT USING (
    id = auth_user_brand_id()
  );

-- Only owners can update brand configuration
DROP POLICY IF EXISTS "brands_update" ON brands;
CREATE POLICY "brands_update" ON brands
  FOR UPDATE USING (
    id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── users ───────────────────────────────────────────────────────────────────

-- Users can see other users in their brand
DROP POLICY IF EXISTS "users_select" ON users;
CREATE POLICY "users_select" ON users
  FOR SELECT USING (
    brand_id = auth_user_brand_id()
  );

-- Only owners can manage users
DROP POLICY IF EXISTS "users_insert" ON users;
CREATE POLICY "users_insert" ON users
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );

DROP POLICY IF EXISTS "users_update" ON users;
CREATE POLICY "users_update" ON users
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );

DROP POLICY IF EXISTS "users_delete" ON users;
CREATE POLICY "users_delete" ON users
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── Generic brand-scoped policies (macro for all brand_id tables) ───────────
-- Applied to: research_runs, research_items, content_drafts, newsletters,
--             campaigns, calendar_events, api_costs, writing_lab_sessions,
--             revenue_deals, pipeline_health, feedback

-- Helper: creates standard RLS policies for a brand-scoped table
-- We define them explicitly for each table for clarity and auditability.

-- ── research_runs ───────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "research_runs_select" ON research_runs;
CREATE POLICY "research_runs_select" ON research_runs
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "research_runs_insert" ON research_runs;
CREATE POLICY "research_runs_insert" ON research_runs
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_runs_update" ON research_runs;
CREATE POLICY "research_runs_update" ON research_runs
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_runs_delete" ON research_runs;
CREATE POLICY "research_runs_delete" ON research_runs
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── research_items ──────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "research_items_select" ON research_items;
CREATE POLICY "research_items_select" ON research_items
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "research_items_insert" ON research_items;
CREATE POLICY "research_items_insert" ON research_items
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_items_update" ON research_items;
CREATE POLICY "research_items_update" ON research_items
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_items_delete" ON research_items;
CREATE POLICY "research_items_delete" ON research_items
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── scores ──────────────────────────────────────────────────────────────────
-- Scores are accessed via research_item_id; we join to check brand ownership

DROP POLICY IF EXISTS "scores_select" ON scores;
CREATE POLICY "scores_select" ON scores
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM research_items ri
      WHERE ri.id = scores.research_item_id
        AND ri.brand_id = auth_user_brand_id()
    )
  );

DROP POLICY IF EXISTS "scores_insert" ON scores;
CREATE POLICY "scores_insert" ON scores
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM research_items ri
      WHERE ri.id = scores.research_item_id
        AND ri.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "scores_update" ON scores;
CREATE POLICY "scores_update" ON scores
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM research_items ri
      WHERE ri.id = scores.research_item_id
        AND ri.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "scores_delete" ON scores;
CREATE POLICY "scores_delete" ON scores
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM research_items ri
      WHERE ri.id = scores.research_item_id
        AND ri.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() = 'owner'
  );


-- ── content_drafts ──────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "content_drafts_select" ON content_drafts;
CREATE POLICY "content_drafts_select" ON content_drafts
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "content_drafts_insert" ON content_drafts;
CREATE POLICY "content_drafts_insert" ON content_drafts
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "content_drafts_update" ON content_drafts;
CREATE POLICY "content_drafts_update" ON content_drafts
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "content_drafts_delete" ON content_drafts;
CREATE POLICY "content_drafts_delete" ON content_drafts
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── god_mode_reviews ────────────────────────────────────────────────────────
-- Access through draft_id -> content_drafts.brand_id

DROP POLICY IF EXISTS "god_mode_reviews_select" ON god_mode_reviews;
CREATE POLICY "god_mode_reviews_select" ON god_mode_reviews
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = god_mode_reviews.draft_id
        AND cd.brand_id = auth_user_brand_id()
    )
  );

DROP POLICY IF EXISTS "god_mode_reviews_insert" ON god_mode_reviews;
CREATE POLICY "god_mode_reviews_insert" ON god_mode_reviews
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = god_mode_reviews.draft_id
        AND cd.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "god_mode_reviews_update" ON god_mode_reviews;
CREATE POLICY "god_mode_reviews_update" ON god_mode_reviews
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = god_mode_reviews.draft_id
        AND cd.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "god_mode_reviews_delete" ON god_mode_reviews;
CREATE POLICY "god_mode_reviews_delete" ON god_mode_reviews
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM content_drafts cd
      WHERE cd.id = god_mode_reviews.draft_id
        AND cd.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() = 'owner'
  );


-- ── newsletters ─────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "newsletters_select" ON newsletters;
CREATE POLICY "newsletters_select" ON newsletters
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "newsletters_insert" ON newsletters;
CREATE POLICY "newsletters_insert" ON newsletters
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletters_update" ON newsletters;
CREATE POLICY "newsletters_update" ON newsletters
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletters_delete" ON newsletters;
CREATE POLICY "newsletters_delete" ON newsletters
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── newsletter_candidates ───────────────────────────────────────────────────
-- Access through newsletter_id -> newsletters.brand_id

DROP POLICY IF EXISTS "newsletter_candidates_select" ON newsletter_candidates;
CREATE POLICY "newsletter_candidates_select" ON newsletter_candidates
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM newsletters n
      WHERE n.id = newsletter_candidates.newsletter_id
        AND n.brand_id = auth_user_brand_id()
    )
  );

DROP POLICY IF EXISTS "newsletter_candidates_insert" ON newsletter_candidates;
CREATE POLICY "newsletter_candidates_insert" ON newsletter_candidates
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM newsletters n
      WHERE n.id = newsletter_candidates.newsletter_id
        AND n.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletter_candidates_update" ON newsletter_candidates;
CREATE POLICY "newsletter_candidates_update" ON newsletter_candidates
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM newsletters n
      WHERE n.id = newsletter_candidates.newsletter_id
        AND n.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletter_candidates_delete" ON newsletter_candidates;
CREATE POLICY "newsletter_candidates_delete" ON newsletter_candidates
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM newsletters n
      WHERE n.id = newsletter_candidates.newsletter_id
        AND n.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() = 'owner'
  );


-- ── campaigns ───────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "campaigns_select" ON campaigns;
CREATE POLICY "campaigns_select" ON campaigns
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "campaigns_insert" ON campaigns;
CREATE POLICY "campaigns_insert" ON campaigns
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "campaigns_update" ON campaigns;
CREATE POLICY "campaigns_update" ON campaigns
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "campaigns_delete" ON campaigns;
CREATE POLICY "campaigns_delete" ON campaigns
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── calendar_events ─────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "calendar_events_select" ON calendar_events;
CREATE POLICY "calendar_events_select" ON calendar_events
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "calendar_events_insert" ON calendar_events;
CREATE POLICY "calendar_events_insert" ON calendar_events
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "calendar_events_update" ON calendar_events;
CREATE POLICY "calendar_events_update" ON calendar_events
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "calendar_events_delete" ON calendar_events;
CREATE POLICY "calendar_events_delete" ON calendar_events
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── api_costs ───────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "api_costs_select" ON api_costs;
CREATE POLICY "api_costs_select" ON api_costs
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "api_costs_insert" ON api_costs;
CREATE POLICY "api_costs_insert" ON api_costs
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

-- No update/delete for cost records (append-only audit log)




-- ── writing_lab_sessions ────────────────────────────────────────────────────

DROP POLICY IF EXISTS "writing_lab_sessions_select" ON writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_select" ON writing_lab_sessions
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "writing_lab_sessions_insert" ON writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_insert" ON writing_lab_sessions
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_sessions_update" ON writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_update" ON writing_lab_sessions
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_sessions_delete" ON writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_delete" ON writing_lab_sessions
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── writing_lab_rounds ──────────────────────────────────────────────────────
-- Access through session_id -> writing_lab_sessions.brand_id

DROP POLICY IF EXISTS "writing_lab_rounds_select" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_select" ON writing_lab_rounds
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM writing_lab_sessions wls
      WHERE wls.id = writing_lab_rounds.session_id
        AND wls.brand_id = auth_user_brand_id()
    )
  );

DROP POLICY IF EXISTS "writing_lab_rounds_insert" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_insert" ON writing_lab_rounds
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM writing_lab_sessions wls
      WHERE wls.id = writing_lab_rounds.session_id
        AND wls.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_rounds_update" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_update" ON writing_lab_rounds
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM writing_lab_sessions wls
      WHERE wls.id = writing_lab_rounds.session_id
        AND wls.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_rounds_delete" ON writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_delete" ON writing_lab_rounds
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM writing_lab_sessions wls
      WHERE wls.id = writing_lab_rounds.session_id
        AND wls.brand_id = auth_user_brand_id()
    )
    AND auth_user_role() = 'owner'
  );


-- ── revenue_deals ───────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "revenue_deals_select" ON revenue_deals;
CREATE POLICY "revenue_deals_select" ON revenue_deals
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "revenue_deals_insert" ON revenue_deals;
CREATE POLICY "revenue_deals_insert" ON revenue_deals
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "revenue_deals_update" ON revenue_deals;
CREATE POLICY "revenue_deals_update" ON revenue_deals
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "revenue_deals_delete" ON revenue_deals;
CREATE POLICY "revenue_deals_delete" ON revenue_deals
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── pipeline_health ─────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "pipeline_health_select" ON pipeline_health;
CREATE POLICY "pipeline_health_select" ON pipeline_health
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "pipeline_health_insert" ON pipeline_health;
CREATE POLICY "pipeline_health_insert" ON pipeline_health
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "pipeline_health_update" ON pipeline_health;
CREATE POLICY "pipeline_health_update" ON pipeline_health
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "pipeline_health_delete" ON pipeline_health;
CREATE POLICY "pipeline_health_delete" ON pipeline_health
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ── feedback ────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "feedback_select" ON feedback;
CREATE POLICY "feedback_select" ON feedback
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "feedback_insert" ON feedback;
CREATE POLICY "feedback_insert" ON feedback
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "feedback_update" ON feedback;
CREATE POLICY "feedback_update" ON feedback
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "feedback_delete" ON feedback;
CREATE POLICY "feedback_delete" ON feedback
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


-- ============================================================================
-- 7. GRANTS
-- ============================================================================

-- Grant usage to authenticated users (anon has no access by default)
GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Service role gets full access (bypasses RLS)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;


-- ============================================================================
-- 8. DONE
-- ============================================================================
-- Migration 001_initial_schema.sql complete.
-- 18 tables, 3 views, 18 enum types, RLS policies on all tables.
-- Next steps:
--   - Seed initial brand and owner user
--   - Configure pg_cron jobs for periodic tasks (e.g., pipeline_health cleanup)
--   - Set up Supabase Edge Functions for auth triggers (user profile creation)
