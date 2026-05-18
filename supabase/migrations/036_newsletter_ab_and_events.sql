-- Migration 036 — A/B campaign tracking + newsletter events table
--
-- Phase 4: Records provider campaign ID, A/B winner, and raw email events
-- (open, click, bounce, unsubscribe) received via webhooks.

-- Add campaign tracking columns to newsletters
ALTER TABLE public.newsletters
  ADD COLUMN IF NOT EXISTS provider_campaign_id text,
  ADD COLUMN IF NOT EXISTS ab_winner           text
    CHECK (ab_winner IN ('a', 'b'));

COMMENT ON COLUMN public.newsletters.provider_campaign_id IS
  'Campaign ID on the email provider (Brevo campaign ID, Mailchimp campaign ID, etc.)';
COMMENT ON COLUMN public.newsletters.ab_winner IS
  'Which subject variant won the A/B test: a | b';

-- Newsletter events table for webhook payloads
CREATE TABLE IF NOT EXISTS public.newsletter_events (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  newsletter_id uuid        NOT NULL REFERENCES public.newsletters(id) ON DELETE CASCADE,
  event_type    text        NOT NULL
                            CHECK (event_type IN ('delivered', 'opened', 'clicked', 'bounced', 'unsubscribed')),
  email         text        NOT NULL DEFAULT '',
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  metadata      jsonb       NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_newsletter_events_newsletter
  ON public.newsletter_events (newsletter_id, event_type);
CREATE INDEX IF NOT EXISTS idx_newsletter_events_occurred
  ON public.newsletter_events (occurred_at DESC);

COMMENT ON TABLE public.newsletter_events IS
  'Raw email events received via provider webhooks (open, click, bounce, unsub).';

-- RLS: read access for brand members only (via newsletter → brand_id)
ALTER TABLE public.newsletter_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "brand members can read newsletter_events"
  ON public.newsletter_events FOR SELECT
  USING (
    newsletter_id IN (
      SELECT id FROM public.newsletters
      WHERE brand_id IN (
        SELECT brand_id FROM public.brand_members WHERE user_id = auth.uid()
      )
    )
  );
