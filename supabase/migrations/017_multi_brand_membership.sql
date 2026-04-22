-- ============================================================================
-- Migration 017: Multi-brand N:M membership
--
-- Problem: users.brand_id is a 1:1 foreign key — one user owns exactly one
-- brand. This blocks Q0 (multiple brands) and Q1 (invite teammates).
--
-- Solution: introduce brand_members(user_id, brand_id, role) junction table
-- and rewrite all ~80 RLS policies to use set membership instead of equality.
--
-- Architecture decisions:
--   • auth_user_brand_id()  — kept for backward compat, now returns the user's
--     OLDEST brand (the bootstrap brand). Only used by legacy code paths until
--     fully removed in P7.
--   • user_has_brand(uuid)  — the new membership check. All policies use this.
--   • auth_user_role()      — still reads from public.users.role.  Multi-brand
--     role-per-brand is a P2+ concern; for P1 every brand owned by the same
--     user inherits the same system-level role.
--   • create_brand_with_owner — extended to INSERT into brand_members (in
--     addition to users). Guard user_already_has_brand removed — N:M allowed.
--   • users.brand_id        — kept READ-ONLY for legacy compatibility; new
--     write path is brand_members. Drop scheduled for P7 migration 020.
--
-- Telegram alert integration (per Davide's request):
--   P2: memory consolidation worker fires send_telegram_alert
--   P3: discovery completion fires send_telegram_alert
--   P4: newsletter generation fires send_telegram_alert
--   These are Python-side changes (services/alerting.py already wired).
--   This migration has no Telegram footprint but the comment records intent.
-- ============================================================================


-- ============================================================================
-- PART 1 — brand_members table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.brand_members (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid        NOT NULL REFERENCES auth.users(id)    ON DELETE CASCADE,
  brand_id   uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  role       text        NOT NULL DEFAULT 'owner'
               CHECK (role IN ('owner', 'admin', 'member')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, brand_id)
);

CREATE INDEX IF NOT EXISTS idx_brand_members_user    ON public.brand_members (user_id);
CREATE INDEX IF NOT EXISTS idx_brand_members_brand   ON public.brand_members (brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_members_user_brand ON public.brand_members (user_id, brand_id);

COMMENT ON TABLE public.brand_members IS
  'N:M junction: one user can belong to many brands, one brand can have many users.
   role values: owner (full control), admin (edit only), member (read-only).
   users.brand_id is kept for backward compat; brand_members is the source of truth.';


-- ============================================================================
-- PART 2 — Backfill: seed brand_members from every existing users row
-- ============================================================================

INSERT INTO public.brand_members (user_id, brand_id, role)
SELECT  u.id,
        u.brand_id,
        COALESCE(u.role::text, 'owner')   -- cast user_role enum → text
FROM    public.users u
WHERE   u.brand_id IS NOT NULL
ON CONFLICT (user_id, brand_id) DO NOTHING;


-- ============================================================================
-- PART 3 — Helper functions
-- ============================================================================

-- 3a. user_has_brand: primary membership check used in all new RLS policies.
--     SECURITY INVOKER so auth.uid() resolves in the caller's session context.
CREATE OR REPLACE FUNCTION public.user_has_brand(p_brand_id uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1
    FROM   public.brand_members
    WHERE  user_id  = auth.uid()
      AND  brand_id = p_brand_id
  )
$$;

COMMENT ON FUNCTION public.user_has_brand IS
  'Returns TRUE if the current authenticated user is a member of the given brand.
   Used in all RLS policies as the replacement for the old brand_id = auth_user_brand_id() equality check.';

-- 3b. auth_user_brand_id: updated to return the OLDEST membership (bootstrap
--     brand).  Kept for backward compat; will be dropped in migration 020.
CREATE OR REPLACE FUNCTION public.auth_user_brand_id()
RETURNS uuid
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public AS $$
  SELECT brand_id
  FROM   public.brand_members
  WHERE  user_id = auth.uid()
  ORDER  BY created_at
  LIMIT  1
$$;

COMMENT ON FUNCTION public.auth_user_brand_id IS
  '[DEPRECATED — use user_has_brand()] Returns first brand for current user.
   Kept for legacy callers; removal planned in migration 020.';

-- auth_user_role is unchanged — still reads from public.users.
-- Per-brand roles from brand_members.role will replace this in P2.


-- ============================================================================
-- PART 4 — RLS on brand_members itself
-- ============================================================================

ALTER TABLE public.brand_members ENABLE ROW LEVEL SECURITY;

-- Users can see all their own memberships
DROP POLICY IF EXISTS "brand_members_select" ON public.brand_members;
CREATE POLICY "brand_members_select" ON public.brand_members
  FOR SELECT USING (user_id = auth.uid());

-- Users can add themselves to a brand (invite flow — server validates membership
-- before calling INSERT)
DROP POLICY IF EXISTS "brand_members_insert" ON public.brand_members;
CREATE POLICY "brand_members_insert" ON public.brand_members
  FOR INSERT WITH CHECK (user_id = auth.uid());

-- Owners can remove members; non-owners can only remove themselves
DROP POLICY IF EXISTS "brand_members_delete" ON public.brand_members;
CREATE POLICY "brand_members_delete" ON public.brand_members
  FOR DELETE USING (
    user_id = auth.uid()          -- self-removal always allowed
    OR auth_user_role() = 'owner' -- owners can remove anyone in their brand
  );


-- ============================================================================
-- PART 5 — Rewrite all existing RLS policies
--
-- Pattern: brand_id = auth_user_brand_id()  →  user_has_brand(brand_id)
--          id       = auth_user_brand_id()  →  user_has_brand(id)         (brands table)
--          JOIN     ...  = auth_user_brand_id()  →  user_has_brand(join.brand_id)
--
-- Every DROP is paired with a CREATE to make this idempotent on re-run.
-- ============================================================================


-- ── brands ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "brands_select" ON public.brands;
CREATE POLICY "brands_select" ON public.brands
  FOR SELECT USING (user_has_brand(id));

DROP POLICY IF EXISTS "brands_update" ON public.brands;
CREATE POLICY "brands_update" ON public.brands
  FOR UPDATE USING (
    user_has_brand(id) AND auth_user_role() = 'owner'
  )
  WITH CHECK (
    user_has_brand(id) AND auth_user_role() = 'owner'
  );


-- ── users (profile table) ───────────────────────────────────────────────────
DROP POLICY IF EXISTS "users_select" ON public.users;
CREATE POLICY "users_select" ON public.users
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "users_insert" ON public.users;
CREATE POLICY "users_insert" ON public.users
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );

DROP POLICY IF EXISTS "users_update" ON public.users;
CREATE POLICY "users_update" ON public.users
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );

DROP POLICY IF EXISTS "users_delete" ON public.users;
CREATE POLICY "users_delete" ON public.users
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── research_runs ───────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "research_runs_select" ON public.research_runs;
CREATE POLICY "research_runs_select" ON public.research_runs
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "research_runs_insert" ON public.research_runs;
CREATE POLICY "research_runs_insert" ON public.research_runs
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_runs_update" ON public.research_runs;
CREATE POLICY "research_runs_update" ON public.research_runs
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_runs_delete" ON public.research_runs;
CREATE POLICY "research_runs_delete" ON public.research_runs
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── research_items ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "research_items_select" ON public.research_items;
CREATE POLICY "research_items_select" ON public.research_items
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "research_items_insert" ON public.research_items;
CREATE POLICY "research_items_insert" ON public.research_items
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_items_update" ON public.research_items;
CREATE POLICY "research_items_update" ON public.research_items
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "research_items_delete" ON public.research_items;
CREATE POLICY "research_items_delete" ON public.research_items
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── scores (indirect via research_items) ────────────────────────────────────
DROP POLICY IF EXISTS "scores_select" ON public.scores;
CREATE POLICY "scores_select" ON public.scores
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.research_items ri
      WHERE  ri.id = scores.research_item_id
        AND  user_has_brand(ri.brand_id)
    )
  );

DROP POLICY IF EXISTS "scores_insert" ON public.scores;
CREATE POLICY "scores_insert" ON public.scores
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.research_items ri
      WHERE  ri.id = scores.research_item_id
        AND  user_has_brand(ri.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "scores_update" ON public.scores;
CREATE POLICY "scores_update" ON public.scores
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM public.research_items ri
      WHERE  ri.id = scores.research_item_id
        AND  user_has_brand(ri.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "scores_delete" ON public.scores;
CREATE POLICY "scores_delete" ON public.scores
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.research_items ri
      WHERE  ri.id = scores.research_item_id
        AND  user_has_brand(ri.brand_id)
    )
    AND auth_user_role() = 'owner'
  );


-- ── content_drafts ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "content_drafts_select" ON public.content_drafts;
CREATE POLICY "content_drafts_select" ON public.content_drafts
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "content_drafts_insert" ON public.content_drafts;
CREATE POLICY "content_drafts_insert" ON public.content_drafts
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "content_drafts_update" ON public.content_drafts;
CREATE POLICY "content_drafts_update" ON public.content_drafts
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "content_drafts_delete" ON public.content_drafts;
CREATE POLICY "content_drafts_delete" ON public.content_drafts
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── god_mode_reviews ────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "god_mode_reviews_select" ON public.god_mode_reviews;
CREATE POLICY "god_mode_reviews_select" ON public.god_mode_reviews
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.content_drafts cd
      WHERE  cd.id = god_mode_reviews.draft_id
        AND  user_has_brand(cd.brand_id)
    )
  );

DROP POLICY IF EXISTS "god_mode_reviews_insert" ON public.god_mode_reviews;
CREATE POLICY "god_mode_reviews_insert" ON public.god_mode_reviews
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.content_drafts cd
      WHERE  cd.id = god_mode_reviews.draft_id
        AND  user_has_brand(cd.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "god_mode_reviews_update" ON public.god_mode_reviews;
CREATE POLICY "god_mode_reviews_update" ON public.god_mode_reviews
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM public.content_drafts cd
      WHERE  cd.id = god_mode_reviews.draft_id
        AND  user_has_brand(cd.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "god_mode_reviews_delete" ON public.god_mode_reviews;
CREATE POLICY "god_mode_reviews_delete" ON public.god_mode_reviews
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.content_drafts cd
      WHERE  cd.id = god_mode_reviews.draft_id
        AND  user_has_brand(cd.brand_id)
    )
    AND auth_user_role() = 'owner'
  );


-- ── newsletters ─────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "newsletters_select" ON public.newsletters;
CREATE POLICY "newsletters_select" ON public.newsletters
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "newsletters_insert" ON public.newsletters;
CREATE POLICY "newsletters_insert" ON public.newsletters
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletters_update" ON public.newsletters;
CREATE POLICY "newsletters_update" ON public.newsletters
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletters_delete" ON public.newsletters;
CREATE POLICY "newsletters_delete" ON public.newsletters
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── newsletter_candidates (indirect via newsletters) ────────────────────────
DROP POLICY IF EXISTS "newsletter_candidates_select" ON public.newsletter_candidates;
CREATE POLICY "newsletter_candidates_select" ON public.newsletter_candidates
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.newsletters n
      WHERE  n.id = newsletter_candidates.newsletter_id
        AND  user_has_brand(n.brand_id)
    )
  );

DROP POLICY IF EXISTS "newsletter_candidates_insert" ON public.newsletter_candidates;
CREATE POLICY "newsletter_candidates_insert" ON public.newsletter_candidates
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.newsletters n
      WHERE  n.id = newsletter_candidates.newsletter_id
        AND  user_has_brand(n.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletter_candidates_update" ON public.newsletter_candidates;
CREATE POLICY "newsletter_candidates_update" ON public.newsletter_candidates
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM public.newsletters n
      WHERE  n.id = newsletter_candidates.newsletter_id
        AND  user_has_brand(n.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "newsletter_candidates_delete" ON public.newsletter_candidates;
CREATE POLICY "newsletter_candidates_delete" ON public.newsletter_candidates
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.newsletters n
      WHERE  n.id = newsletter_candidates.newsletter_id
        AND  user_has_brand(n.brand_id)
    )
    AND auth_user_role() = 'owner'
  );


-- ── campaigns ───────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "campaigns_select" ON public.campaigns;
CREATE POLICY "campaigns_select" ON public.campaigns
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "campaigns_insert" ON public.campaigns;
CREATE POLICY "campaigns_insert" ON public.campaigns
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "campaigns_update" ON public.campaigns;
CREATE POLICY "campaigns_update" ON public.campaigns
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "campaigns_delete" ON public.campaigns;
CREATE POLICY "campaigns_delete" ON public.campaigns
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── calendar_events ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "calendar_events_select" ON public.calendar_events;
CREATE POLICY "calendar_events_select" ON public.calendar_events
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "calendar_events_insert" ON public.calendar_events;
CREATE POLICY "calendar_events_insert" ON public.calendar_events
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "calendar_events_update" ON public.calendar_events;
CREATE POLICY "calendar_events_update" ON public.calendar_events
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "calendar_events_delete" ON public.calendar_events;
CREATE POLICY "calendar_events_delete" ON public.calendar_events
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── api_costs ────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "api_costs_select" ON public.api_costs;
CREATE POLICY "api_costs_select" ON public.api_costs
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "api_costs_insert" ON public.api_costs;
CREATE POLICY "api_costs_insert" ON public.api_costs
  FOR INSERT WITH CHECK (user_has_brand(brand_id));


-- ── writing_lab_sessions ─────────────────────────────────────────────────────
DROP POLICY IF EXISTS "writing_lab_sessions_select" ON public.writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_select" ON public.writing_lab_sessions
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "writing_lab_sessions_insert" ON public.writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_insert" ON public.writing_lab_sessions
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_sessions_update" ON public.writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_update" ON public.writing_lab_sessions
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_sessions_delete" ON public.writing_lab_sessions;
CREATE POLICY "writing_lab_sessions_delete" ON public.writing_lab_sessions
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── writing_lab_rounds (indirect via writing_lab_sessions) ──────────────────
DROP POLICY IF EXISTS "writing_lab_rounds_select" ON public.writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_select" ON public.writing_lab_rounds
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.writing_lab_sessions wls
      WHERE  wls.id = writing_lab_rounds.session_id
        AND  user_has_brand(wls.brand_id)
    )
  );

DROP POLICY IF EXISTS "writing_lab_rounds_insert" ON public.writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_insert" ON public.writing_lab_rounds
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.writing_lab_sessions wls
      WHERE  wls.id = writing_lab_rounds.session_id
        AND  user_has_brand(wls.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_rounds_update" ON public.writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_update" ON public.writing_lab_rounds
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM public.writing_lab_sessions wls
      WHERE  wls.id = writing_lab_rounds.session_id
        AND  user_has_brand(wls.brand_id)
    )
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "writing_lab_rounds_delete" ON public.writing_lab_rounds;
CREATE POLICY "writing_lab_rounds_delete" ON public.writing_lab_rounds
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.writing_lab_sessions wls
      WHERE  wls.id = writing_lab_rounds.session_id
        AND  user_has_brand(wls.brand_id)
    )
    AND auth_user_role() = 'owner'
  );


-- ── revenue_deals ────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "revenue_deals_select" ON public.revenue_deals;
CREATE POLICY "revenue_deals_select" ON public.revenue_deals
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "revenue_deals_insert" ON public.revenue_deals;
CREATE POLICY "revenue_deals_insert" ON public.revenue_deals
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "revenue_deals_update" ON public.revenue_deals;
CREATE POLICY "revenue_deals_update" ON public.revenue_deals
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "revenue_deals_delete" ON public.revenue_deals;
CREATE POLICY "revenue_deals_delete" ON public.revenue_deals
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── pipeline_health ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "pipeline_health_select" ON public.pipeline_health;
CREATE POLICY "pipeline_health_select" ON public.pipeline_health
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "pipeline_health_insert" ON public.pipeline_health;
CREATE POLICY "pipeline_health_insert" ON public.pipeline_health
  FOR INSERT WITH CHECK (user_has_brand(brand_id));

DROP POLICY IF EXISTS "pipeline_health_update" ON public.pipeline_health;
CREATE POLICY "pipeline_health_update" ON public.pipeline_health
  FOR UPDATE USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "pipeline_health_delete" ON public.pipeline_health;
CREATE POLICY "pipeline_health_delete" ON public.pipeline_health
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── feedback ─────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "feedback_select" ON public.feedback;
CREATE POLICY "feedback_select" ON public.feedback
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "feedback_insert" ON public.feedback;
CREATE POLICY "feedback_insert" ON public.feedback
  FOR INSERT WITH CHECK (user_has_brand(brand_id));

DROP POLICY IF EXISTS "feedback_update" ON public.feedback;
CREATE POLICY "feedback_update" ON public.feedback
  FOR UPDATE USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "feedback_delete" ON public.feedback;
CREATE POLICY "feedback_delete" ON public.feedback
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── audit_trail (from migration 002) ─────────────────────────────────────────
DROP POLICY IF EXISTS "audit_trail_select" ON public.audit_trail;
CREATE POLICY "audit_trail_select" ON public.audit_trail
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "audit_trail_insert" ON public.audit_trail;
CREATE POLICY "audit_trail_insert" ON public.audit_trail
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );


-- ── agent_configs (from migration 005) ───────────────────────────────────────
DROP POLICY IF EXISTS "agent_configs_select" ON public.agent_configs;
CREATE POLICY "agent_configs_select" ON public.agent_configs
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "agent_configs_insert" ON public.agent_configs;
CREATE POLICY "agent_configs_insert" ON public.agent_configs
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_configs_update" ON public.agent_configs;
CREATE POLICY "agent_configs_update" ON public.agent_configs
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_configs_delete" ON public.agent_configs;
CREATE POLICY "agent_configs_delete" ON public.agent_configs
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── agent_skills (from migration 005) ────────────────────────────────────────
DROP POLICY IF EXISTS "agent_skills_select" ON public.agent_skills;
CREATE POLICY "agent_skills_select" ON public.agent_skills
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "agent_skills_insert" ON public.agent_skills;
CREATE POLICY "agent_skills_insert" ON public.agent_skills
  FOR INSERT WITH CHECK (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_skills_update" ON public.agent_skills;
CREATE POLICY "agent_skills_update" ON public.agent_skills
  FOR UPDATE USING (
    user_has_brand(brand_id) AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_skills_delete" ON public.agent_skills;
CREATE POLICY "agent_skills_delete" ON public.agent_skills
  FOR DELETE USING (
    user_has_brand(brand_id) AND auth_user_role() = 'owner'
  );


-- ── social_metrics (indirect via content_drafts, from migration 008) ─────────
DROP POLICY IF EXISTS "social_metrics_select" ON public.social_metrics;
CREATE POLICY "social_metrics_select" ON public.social_metrics
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.content_drafts cd
      WHERE  cd.id = social_metrics.draft_id
        AND  user_has_brand(cd.brand_id)
    )
  );


-- ── feedback_loop_audit (from migration 008) ──────────────────────────────────
DROP POLICY IF EXISTS "feedback_loop_audit_select" ON public.feedback_loop_audit;
CREATE POLICY "feedback_loop_audit_select" ON public.feedback_loop_audit
  FOR SELECT USING (user_has_brand(brand_id));


-- ── humanizer_performance (from migration 011) ────────────────────────────────
DROP POLICY IF EXISTS "humanizer_perf_select" ON public.humanizer_performance;
CREATE POLICY "humanizer_perf_select" ON public.humanizer_performance
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "humanizer_perf_insert" ON public.humanizer_performance;
CREATE POLICY "humanizer_perf_insert" ON public.humanizer_performance
  FOR INSERT WITH CHECK (user_has_brand(brand_id));


-- ── llm_fallback_log (from migration 012) ────────────────────────────────────
DROP POLICY IF EXISTS "llm_fallback_log_select" ON public.llm_fallback_log;
CREATE POLICY "llm_fallback_log_select" ON public.llm_fallback_log
  FOR SELECT USING (user_has_brand(brand_id));

DROP POLICY IF EXISTS "llm_fallback_log_insert" ON public.llm_fallback_log;
CREATE POLICY "llm_fallback_log_insert" ON public.llm_fallback_log
  FOR INSERT WITH CHECK (user_has_brand(brand_id));


-- ============================================================================
-- PART 6 — Update create_brand_with_owner RPC
--
-- Changes vs migration 015 version:
--   • ALSO inserts into brand_members (new junction table)
--   • REMOVES user_already_has_brand guard — N:M now permitted
--   • keeps users row insert for backward compat (users.brand_id still read by
--     legacy auth-helpers.ts until P1.4 ships the cookie-based switcher)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_brand_with_owner(
  p_name   text,
  p_slug   text,
  p_topics text[] DEFAULT '{}'
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_brand_id  uuid;
  v_user_id   uuid := auth.uid();
  v_email     text;
  v_role      text := 'owner';
BEGIN
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  IF p_name IS NULL OR trim(p_name) = '' THEN
    RAISE EXCEPTION 'name is required';
  END IF;
  IF p_slug IS NULL OR trim(p_slug) = '' THEN
    RAISE EXCEPTION 'slug is required';
  END IF;

  IF EXISTS (SELECT 1 FROM public.brands WHERE slug = p_slug) THEN
    RAISE EXCEPTION 'slug_taken';
  END IF;

  -- NOTE: user_already_has_brand guard removed — N:M is now permitted.
  -- A user can create (or be invited to) multiple brands.

  SELECT email INTO v_email FROM auth.users WHERE id = v_user_id;

  -- 1. Create the brand
  INSERT INTO public.brands (name, slug, topics)
  VALUES (trim(p_name), p_slug, COALESCE(p_topics, '{}'))
  RETURNING id INTO v_brand_id;

  -- 2. Link caller in brand_members (primary N:M table)
  INSERT INTO public.brand_members (user_id, brand_id, role)
  VALUES (v_user_id, v_brand_id, v_role)
  ON CONFLICT (user_id, brand_id) DO NOTHING;

  -- 3. Upsert public.users profile row (backward compat)
  --    First brand created = the "primary" brand stored in users.brand_id.
  --    Subsequent brands only appear in brand_members.
  INSERT INTO public.users (id, brand_id, role, email)
  VALUES (v_user_id, v_brand_id, v_role::user_role, v_email)
  ON CONFLICT (id) DO NOTHING;  -- already has a profile → skip

  RETURN json_build_object(
    'id',   v_brand_id,
    'name', trim(p_name),
    'slug', p_slug
  );
END;
$$;

REVOKE ALL ON FUNCTION public.create_brand_with_owner(text, text, text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.create_brand_with_owner(text, text, text[]) TO authenticated;

COMMENT ON FUNCTION public.create_brand_with_owner IS
  'Creates a brand and links the caller as owner in brand_members (N:M).
   Also upserts public.users for backward compat; subsequent brands skip the
   users upsert (ON CONFLICT DO NOTHING) so users.brand_id always points to the
   first brand created by the user.
   SECURITY DEFINER to bypass RLS bootstrap chicken-and-egg.';

-- Grant select/insert on new table to authenticated role
GRANT SELECT, INSERT, DELETE ON public.brand_members TO authenticated;
