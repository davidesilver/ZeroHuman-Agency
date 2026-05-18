-- Migration 037 — Notification events table
--
-- Stores system-level pipeline events for Telegram digest composition
-- and the dashboard activity feed. Distinct from newsletter_events
-- (which tracks ESP webhook payloads like opens/clicks).

CREATE TABLE IF NOT EXISTS public.notification_events (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        REFERENCES public.brands(id) ON DELETE CASCADE,
  event_type   text        NOT NULL,
  severity     text        NOT NULL DEFAULT 'info'
               CHECK (severity IN ('info', 'success', 'warning', 'error')),
  title        text        NOT NULL DEFAULT '',
  detail       jsonb       NOT NULL DEFAULT '{}',
  entity_type  text,
  entity_id    text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_events_brand
  ON public.notification_events (brand_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_events_created
  ON public.notification_events (created_at DESC);

COMMENT ON TABLE public.notification_events IS
  'System-level pipeline events used for Telegram digest and dashboard activity feed.';

ALTER TABLE public.notification_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "brand members can read notification_events"
  ON public.notification_events FOR SELECT
  USING (
    brand_id IS NULL
    OR brand_id IN (
      SELECT brand_id FROM public.brand_members WHERE user_id = auth.uid()
    )
  );
