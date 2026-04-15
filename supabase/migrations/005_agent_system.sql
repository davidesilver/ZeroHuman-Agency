-- ============================================================================
-- AI Content Engine - Agent System DB
-- Migration: 005_agent_system.sql
-- Description: Agent identity configuration per brand and composable skills
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Agent configs and versions
-- ----------------------------------------------------------------------------

-- Agent identity configuration per brand
CREATE TABLE IF NOT EXISTS agent_configs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_key           TEXT NOT NULL,
  agent_name          TEXT NOT NULL,
  identity            TEXT NOT NULL DEFAULT '',
  task_type_override  TEXT,  -- override del task_type per questo agente+brand
  is_active           BOOLEAN NOT NULL DEFAULT true,
  version             INTEGER NOT NULL DEFAULT 1,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(brand_id, agent_key)
);

-- Versioning per rollback
CREATE TABLE IF NOT EXISTS agent_config_versions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_id   UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
  identity    TEXT NOT NULL,
  version     INTEGER NOT NULL,
  changed_by  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Agent skills con conflict detection
CREATE TABLE IF NOT EXISTS agent_skills (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  skill_name      TEXT NOT NULL,
  target_agent    TEXT NOT NULL,
  priority        TEXT NOT NULL DEFAULT 'medium'
                  CHECK (priority IN ('high', 'medium', 'low')),
  instructions    TEXT NOT NULL DEFAULT '',
  tags            TEXT[] DEFAULT '{}',
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 2. Indexes & RLS
-- ----------------------------------------------------------------------------

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_configs_brand ON agent_configs(brand_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_agent_skills_brand ON agent_skills(brand_id, target_agent);

-- RLS Policies (brand isolation)
ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_skills ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_configs_select" ON agent_configs;
CREATE POLICY "agent_configs_select" ON agent_configs
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "agent_configs_insert" ON agent_configs;
CREATE POLICY "agent_configs_insert" ON agent_configs
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_configs_update" ON agent_configs;
CREATE POLICY "agent_configs_update" ON agent_configs
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_configs_delete" ON agent_configs;
CREATE POLICY "agent_configs_delete" ON agent_configs
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );


DROP POLICY IF EXISTS "agent_skills_select" ON agent_skills;
CREATE POLICY "agent_skills_select" ON agent_skills
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "agent_skills_insert" ON agent_skills;
CREATE POLICY "agent_skills_insert" ON agent_skills
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_skills_update" ON agent_skills;
CREATE POLICY "agent_skills_update" ON agent_skills
  FOR UPDATE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );

DROP POLICY IF EXISTS "agent_skills_delete" ON agent_skills;
CREATE POLICY "agent_skills_delete" ON agent_skills
  FOR DELETE USING (
    brand_id = auth_user_brand_id()
    AND auth_user_role() = 'owner'
  );

-- ----------------------------------------------------------------------------
-- 3. Initial Seeding
-- ----------------------------------------------------------------------------

-- Seed 7 agenti per ogni brand esistente
INSERT INTO agent_configs (brand_id, agent_key, agent_name, identity)
SELECT 
  b.id, a.agent_key, a.agent_name, a.default_identity
FROM brands b
CROSS JOIN (VALUES
  ('writer',        'Writer',           'Sei il Writer del brand — il braccio destro del founder nella comunicazione digitale.'),
  ('editor',        'Editor',           'Sei l''Editor — il guardiano della qualità e della coerenza del brand.'),
  ('adapter',       'Adapter',          'Sei l''Adapter — lo specialista multi-piattaforma del brand.'),
  ('god_advocate',  'GOD Advocate',     'Sei l''Avvocato del Diavolo del GOD System — il contrappeso intellettuale.'),
  ('god_factcheck', 'GOD Fact-Checker', 'Sei il Fact-Checker del GOD System — la sentinella della verità fattuale.'),
  ('god_creative',  'GOD Creative',     'Sei il Direttore Creativo del GOD System — l''alchimista del contenuto.'),
  ('god_synthesis', 'GOD Synthesis',    'Sei il Sintetizzatore del GOD System — il maestro d''orchestra finale.')
) AS a(agent_key, agent_name, default_identity)
ON CONFLICT (brand_id, agent_key) DO NOTHING;
