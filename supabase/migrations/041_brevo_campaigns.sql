-- Migration 041: brevo_campaigns table for email campaign tracking.

BEGIN;

CREATE TABLE IF NOT EXISTS brevo_campaigns (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id         uuid REFERENCES content_drafts(id) ON DELETE SET NULL,
  brevo_campaign_id bigint,             -- Brevo's numeric campaign ID
  name             text NOT NULL,
  subject          text,
  status           text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','scheduled','sent','archived')),
  scheduled_at     timestamptz,
  sent_at          timestamptz,
  recipient_count  integer,
  metrics          jsonb DEFAULT '{}',  -- opens, clicks, bounces, unsubscribes from Brevo webhook
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brevo_campaigns_brand ON brevo_campaigns(brand_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_brevo_campaigns_brevo_id ON brevo_campaigns(brevo_campaign_id) WHERE brevo_campaign_id IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_brevo_campaigns_updated_at') THEN
    CREATE TRIGGER trg_brevo_campaigns_updated_at
      BEFORE UPDATE ON brevo_campaigns
      FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END $$;

ALTER TABLE brevo_campaigns ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS brevo_campaigns_brand ON brevo_campaigns;
CREATE POLICY brevo_campaigns_brand ON brevo_campaigns
  FOR ALL USING (public.user_has_brand(brand_id));

COMMIT;
