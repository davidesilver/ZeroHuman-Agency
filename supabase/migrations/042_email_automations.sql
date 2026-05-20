-- Migration 042: email_automations table for Brevo multi-step workflows.

BEGIN;

CREATE TABLE IF NOT EXISTS email_automations (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name                text NOT NULL,
  template_key        text NOT NULL CHECK (template_key IN ('welcome', 'nurture', 'win-back')),
  status              text NOT NULL DEFAULT 'inactive' CHECK (status IN ('active','inactive')),
  brevo_workflow_id   bigint,            -- Brevo automation/workflow ID when mapped
  steps               jsonb NOT NULL DEFAULT '[]',  -- array of { delay_days, subject, html_content }
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),

  CONSTRAINT uq_email_automations_brand_template UNIQUE (brand_id, template_key)
);

CREATE INDEX IF NOT EXISTS idx_email_automations_brand ON email_automations(brand_id);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_email_automations_updated_at') THEN
    CREATE TRIGGER trg_email_automations_updated_at
      BEFORE UPDATE ON email_automations
      FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END $$;

ALTER TABLE email_automations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS email_automations_brand ON email_automations;
CREATE POLICY email_automations_brand ON email_automations
  FOR ALL USING (public.user_has_brand(brand_id));

COMMIT;
