-- =============================================================================
-- ZEROHUMAN DEMO SEED
-- Popola il DB con dati realistici per screenshot e GIF di marketing.
--
-- Come usarlo:
--   1. Vai su https://supabase.com/dashboard → SQL Editor
--   2. Incolla questo intero file ed esegui
--   3. Poi vai su http://localhost:3080 per vedere l'app popolata
--
-- ATTENZIONE: questo script usa RLS bypass via service role.
-- Esegui SOLO in ambiente dev/demo — mai in produzione.
-- =============================================================================

DO $$
DECLARE
  demo_brand_id   uuid := '00000000-0000-0000-0000-000000000001';
  demo_user_id    uuid; -- filled from auth.users
  run_id_1        uuid := gen_random_uuid();
  run_id_2        uuid := gen_random_uuid();
  item_1          uuid := gen_random_uuid();
  item_2          uuid := gen_random_uuid();
  item_3          uuid := gen_random_uuid();
  item_4          uuid := gen_random_uuid();
  item_5          uuid := gen_random_uuid();
  item_6          uuid := gen_random_uuid();
  item_7          uuid := gen_random_uuid();
  item_8          uuid := gen_random_uuid();
  draft_1         uuid := gen_random_uuid();
  draft_2         uuid := gen_random_uuid();
  draft_3         uuid := gen_random_uuid();
  draft_4         uuid := gen_random_uuid();
  draft_5         uuid := gen_random_uuid();
  draft_6         uuid := gen_random_uuid();
BEGIN

-- ── 1. Get current user ──────────────────────────────────────────────────────
SELECT id INTO demo_user_id FROM auth.users LIMIT 1;

IF demo_user_id IS NULL THEN
  RAISE EXCEPTION 'No user found. Log in at least once before running this seed.';
END IF;

-- ── 2. Brand ─────────────────────────────────────────────────────────────────
INSERT INTO brands (id, name, slug, topics, tone_of_voice, scoring_weights, rss_sources)
VALUES (
  demo_brand_id,
  'ZeroHuman Demo',
  'zerohuman-demo',
  ARRAY['AI', 'content automation', 'marketing ops', 'open source', 'SaaS'],
  '{"register": "professional but direct", "personality": "builder who shows the work", "avoid": ["fluff", "hype", "corporate speak"], "use": ["concrete examples", "numbers", "build-in-public format"]}'::jsonb,
  '{"relevance": 0.35, "credibility": 0.25, "trend_signal": 0.20, "brand_alignment": 0.20}'::jsonb,
  '[
    {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "active": true},
    {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "active": true},
    {"url": "https://feeds.feedburner.com/oreilly/radar", "name": "O''Reilly Radar", "active": true}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- ── 3. Brand membership ──────────────────────────────────────────────────────
INSERT INTO brand_members (brand_id, user_id, role)
VALUES (demo_brand_id, demo_user_id, 'owner')
ON CONFLICT (brand_id, user_id) DO NOTHING;

-- ── 4. Research runs ─────────────────────────────────────────────────────────
INSERT INTO research_runs (id, brand_id, status, retrievers_used, items_found, items_scored, duration_ms, created_at)
VALUES
  (run_id_1, demo_brand_id, 'completed', ARRAY['rss', 'serper', 'youtube', 'duckduckgo'], 24, 24, 8420, now() - interval '2 days'),
  (run_id_2, demo_brand_id, 'completed', ARRAY['rss', 'serper', 'tavily', 'competitor'], 31, 31, 9140, now() - interval '1 day');

-- ── 5. Research items ────────────────────────────────────────────────────────
INSERT INTO research_items (id, brand_id, run_id, url, title, summary, source_name, source_type, retriever_type, status, created_at)
VALUES
  (item_1, demo_brand_id, run_id_2,
   'https://techcrunch.com/2026/05/ai-content-ops-tools',
   'The AI Content Ops Tools Taking Over Marketing Teams in 2026',
   'A deep look at how autonomous content platforms are replacing 6-tool stacks. Jasper, Copy.ai, and newcomers like ZeroHuman are competing for the content ops market.',
   'TechCrunch', 'rss', 'rss', 'approved', now() - interval '22 hours'),

  (item_2, demo_brand_id, run_id_2,
   'https://twitter.com/levelsio/status/ai-content-post',
   'Pieter Levels: "Built an AI content engine that writes 3 posts/day. Revenue went up 40%."',
   'Indie hacker thread on automating content marketing. 12k likes. Mentions multi-agent review as the key differentiator.',
   'X (Twitter)', 'scrape', 'x', 'approved', now() - interval '20 hours'),

  (item_3, demo_brand_id, run_id_2,
   'https://www.youtube.com/watch?v=ai-marketing-2026',
   'I Automated My Entire Content Strategy (6-Month Results)',
   'YouTube creator shares before/after metrics: 2h/day → 20min, 3x content output, engagement up. Comments asking about the tool stack.',
   'YouTube', 'youtube', 'youtube', 'scored', now() - interval '18 hours'),

  (item_4, demo_brand_id, run_id_2,
   'https://hn.algolia.com/ai-writing-tools-2026',
   'Ask HN: What''s the best open-source alternative to Jasper?',
   'HN thread with 280+ comments. Top answers: build your own pipeline, ZeroHuman mentioned twice, general consensus that proprietary tools are overpriced.',
   'Hacker News', 'search', 'duckduckgo', 'approved', now() - interval '15 hours'),

  (item_5, demo_brand_id, run_id_2,
   'https://www.producthunt.com/posts/ai-content-engine',
   'AI Content Engines — Product Hunt Weekly Digest',
   'ProductHunt roundup of content automation tools launched this week. 5 new tools, all cloud-only. Self-hosted gap noted in comments.',
   'Product Hunt', 'scrape', 'serper', 'scored', now() - interval '12 hours'),

  (item_6, demo_brand_id, run_id_1,
   'https://substack.com/ai-content-agencies',
   'How Agencies Are Using AI Content Tools in 2026',
   'Survey of 200+ marketing agencies: 78% use AI for content, but 64% still manage multiple tools. Multi-tenancy is the #1 requested feature.',
   'Substack', 'rss', 'tavily', 'rejected', now() - interval '2 days'),

  (item_7, demo_brand_id, run_id_1,
   'https://www.sequoia.com/ai-content-market-map',
   'The AI Content Market Map: Who Wins?',
   'Sequoia analysis of the content AI landscape. Key insight: open-source players have 3x lower CAC. Enterprise buyers prefer self-hosted for data privacy.',
   'Sequoia Capital', 'search', 'serper', 'approved', now() - interval '2 days'),

  (item_8, demo_brand_id, run_id_1,
   'https://competitor.example.com/blog/vs-zerohuman',
   'ZeroHuman vs Jasper: Which is Better for Agencies?',
   'Competitor comparison article. Favors their tool but acknowledges ZeroHuman''s multi-tenancy and self-hosted advantages.',
   'Competitor Blog', 'scrape', 'competitor', 'archived', now() - interval '2 days');

-- ── 6. Scores for research items ─────────────────────────────────────────────
INSERT INTO scores (research_item_id, brand_id, relevance, credibility, trend_signal, brand_alignment, composite, version, created_at)
VALUES
  (item_1, demo_brand_id, 0.91, 0.88, 0.82, 0.90, 0.88, 1, now() - interval '22 hours'),
  (item_2, demo_brand_id, 0.86, 0.79, 0.94, 0.85, 0.86, 1, now() - interval '20 hours'),
  (item_3, demo_brand_id, 0.82, 0.76, 0.88, 0.80, 0.81, 1, now() - interval '18 hours'),
  (item_4, demo_brand_id, 0.94, 0.85, 0.78, 0.92, 0.88, 1, now() - interval '15 hours'),
  (item_5, demo_brand_id, 0.74, 0.82, 0.71, 0.76, 0.76, 1, now() - interval '12 hours'),
  (item_6, demo_brand_id, 0.55, 0.90, 0.60, 0.58, 0.64, 1, now() - interval '2 days'),
  (item_7, demo_brand_id, 0.89, 0.95, 0.85, 0.88, 0.89, 1, now() - interval '2 days'),
  (item_8, demo_brand_id, 0.70, 0.65, 0.55, 0.72, 0.66, 1, now() - interval '2 days');

-- ── 7. Content drafts ────────────────────────────────────────────────────────
INSERT INTO content_drafts (id, brand_id, research_item_id, content_type, platform, title, body, status, seo_score, scheduled_at, created_at)
VALUES

-- Draft 1: published LinkedIn post
(draft_1, demo_brand_id, item_7,
 'social_post', 'linkedin',
 'The open-source AI content market is heating up',
 E'Sequoia just mapped the AI content market. Their key finding:\n\nOpen-source players have 3x lower CAC than proprietary SaaS.\n\nEnterprise buyers increasingly prefer self-hosted tools for data privacy.\n\nThe market is splitting:\n→ $49/month cloud tools for individuals\n→ Self-hosted platforms for teams who own their data\n\nZeroHuman sits in the second category. MIT license, Docker-based, full pipeline from research to publish.\n\nIf you\'re building content for clients, your API keys and their data shouldn\'t be on someone else\'s server.\n\nhttps://github.com/davidesilver/ZeroHuman-Agency\n\n#OpenSource #ContentMarketing #AI',
 'published', 84, null, now() - interval '2 days'),

-- Draft 2: scheduled LinkedIn post (GOD Mode approved)
(draft_2, demo_brand_id, item_4,
 'social_post', 'linkedin',
 'HN agrees: proprietary content tools are overpriced',
 E'280+ comments on Hacker News asking: "What''s the best open-source alternative to Jasper?"\n\nTop consensus:\n1. Build your own pipeline\n2. ZeroHuman (mentioned multiple times)\n3. "Jasper is $125/month for something you can run yourself"\n\nThe developer community has spoken. If you\'re technical, there''s no reason to pay recurring fees for AI writing tools.\n\nZeroHuman is the answer: MIT license, full pipeline, multi-agent review, self-hosted.\n\nhttps://github.com/davidesilver/ZeroHuman-Agency',
 'scheduled', 91, now() + interval '1 day 9 hours', now() - interval '14 hours'),

-- Draft 3: approved, awaiting publish
(draft_3, demo_brand_id, item_1,
 'social_post', 'x',
 'AI content ops is the new martech category',
 E'🧵 TechCrunch just called it: AI Content Ops is the new martech category.\n\n6 tools are becoming 1 platform:\n- Research (Feedly → built-in)\n- Draft (ChatGPT → multi-agent pipeline)\n- Edit (Grammarly → humanizer)\n- Schedule (Buffer → calendar)\n- Newsletter (Mailchimp → built-in)\n- Track (Sheets → feedback loop)\n\nZeroHuman does all of this. MIT license. Self-hosted.\n\n⭐ https://github.com/davidesilver/ZeroHuman-Agency',
 'approved', 88, null, now() - interval '10 hours'),

-- Draft 4: in GOD mode review
(draft_4, demo_brand_id, item_2,
 'social_post', 'linkedin',
 '40% revenue increase from AI content automation',
 E'Pieter Levels posted a thread that got 12k likes:\n\n"Built an AI content engine that writes 3 posts/day. Revenue went up 40%."\n\nThe comments are full of people asking how. The answer isn''t the volume — it''s the quality control.\n\nAnyone can generate 3 posts/day with ChatGPT. The hard part is making them good enough to publish without manual editing for every single one.\n\nThat''s what multi-agent review solves. 4 agents, each with one job:\n→ Critic: structure and argument\n→ Fact-checker: verify every claim\n→ Creative: stronger hooks\n→ Synthesis: top 3 changes that matter\n\nWe built this into ZeroHuman. Open source, MIT.\nhttps://github.com/davidesilver/ZeroHuman-Agency',
 'god_mode', 76, null, now() - interval '6 hours'),

-- Draft 5: draft (blog post)
(draft_5, demo_brand_id, item_4,
 'blog_post', 'blog',
 'Why the developer community is abandoning proprietary AI writing tools',
 E'# Why the developer community is abandoning proprietary AI writing tools\n\nA Hacker News thread asked a simple question last week: "What''s the best open-source alternative to Jasper?"\n\n280 comments later, the consensus is clear: developers don''t want to pay recurring fees for AI writing infrastructure they can run themselves.\n\n## The cost problem\n\nJasper charges $49-125/month. Copy.ai starts at $49/month. For a single developer or small team, that''s $588-$1,500/year for tooling that, at its core, is a wrapper around an LLM API you''re already paying for.\n\n## The control problem\n\nWhen you use a SaaS content tool, your brand voice data, your content history, and your API keys live on someone else''s server. For agencies managing client data, this is an unacceptable risk.\n\n## The flexibility problem\n\nProprietary tools optimize for the median user. If you need custom scoring logic, a specific retriever, or integration with your internal systems, you''re blocked.\n\n## The open-source answer\n\nZeroHuman is MIT-licensed, self-hosted, and built for teams who want control...',
 'draft', 72, null, now() - interval '4 hours'),

-- Draft 6: draft newsletter
(draft_6, demo_brand_id, item_7,
 'newsletter', 'email',
 'AI Content Ops Weekly #4 — The market map issue',
 E'# AI Content Ops Weekly #4\n\n**This week:** Sequoia maps the market, HN debates open source, and we ship GOD Mode.\n\n---\n\n## 📊 Sequoia''s AI Content Market Map\n\nThe big takeaway: open-source players have 3x lower CAC. The enterprise market is moving to self-hosted. Full analysis inside.\n\n## 🛠 What we shipped this week\n\n- **GOD Mode v2**: Fact-checker now cites sources inline\n- **Humanizer**: Gold example upload UX improved\n- **Research pipeline**: Competitor spider now handles paywalled content\n\n## 📈 Numbers\n\n- GitHub stars: 847 (up 210 this week)\n- Issues closed: 12\n- Contributors: 6 (3 new)\n\n---\n\nBuilding in public. See you next week.\n\n— Davide',
 'draft', null, null, now() - interval '2 hours');

-- ── 8. GOD Mode result for draft_4 ───────────────────────────────────────────
UPDATE content_drafts
SET god_mode_result = '{
  "verdict": "needs_revision",
  "overall_score": 74,
  "critic": {
    "score": 72,
    "issues": [
      "Opening hook leads with someone else''s achievement — reframe around your product value",
      "Fourth paragraph buries the key differentiator (multi-agent review). Move it earlier.",
      "No concrete comparison: how does this differ from running GOD Mode on ChatGPT output?"
    ]
  },
  "fact_checker": {
    "score": 88,
    "issues": [
      "\"12k likes\" — verify current count before publishing, social metrics change",
      "\"40% revenue increase\" — Levels'' claim, not verified independently. Add qualifier."
    ]
  },
  "creative": {
    "score": 71,
    "suggestions": [
      "Open with the number: \"40% revenue. 3 posts/day. Here''s the part everyone misses:\"",
      "Add a before/after: \"Before: 2h editing each post. After: 4 agents do it in 30 seconds.\"",
      "The CTA is weak. Replace with a specific question: \"What''s stopping you from running this yourself?\""
    ]
  },
  "synthesis": {
    "priority_actions": [
      "Rewrite opening to lead with the gap (manual editing) not Levels'' achievement",
      "Add before/after framing to make the value concrete",
      "Verify and qualify the 40% claim"
    ]
  }
}'::jsonb
WHERE id = draft_4;

-- ── 9. Pipeline health ───────────────────────────────────────────────────────
INSERT INTO pipeline_health (brand_id, component, status, latency_ms, error_rate, last_checked_at)
VALUES
  (demo_brand_id, 'research', 'healthy', 1240, 0.02, now() - interval '5 minutes'),
  (demo_brand_id, 'scoring', 'healthy', 380, 0.00, now() - interval '5 minutes'),
  (demo_brand_id, 'generation', 'healthy', 2840, 0.03, now() - interval '5 minutes'),
  (demo_brand_id, 'publishing', 'healthy', 890, 0.01, now() - interval '5 minutes')
ON CONFLICT (brand_id, component) DO UPDATE
  SET status = EXCLUDED.status,
      latency_ms = EXCLUDED.latency_ms,
      error_rate = EXCLUDED.error_rate,
      last_checked_at = EXCLUDED.last_checked_at;

-- ── 10. API costs ─────────────────────────────────────────────────────────────
INSERT INTO api_costs (brand_id, provider, model, operation, input_tokens, output_tokens, cost_usd, created_at)
VALUES
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'research_scoring', 12400, 2100, 0.0420, now() - interval '2 days'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'content_generation', 8200, 4800, 0.0612, now() - interval '2 days'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'god_mode_review', 6800, 3200, 0.0480, now() - interval '2 days'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'humanizer', 4100, 1900, 0.0276, now() - interval '2 days'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'research_scoring', 14800, 2600, 0.0504, now() - interval '1 day'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'content_generation', 9400, 5200, 0.0696, now() - interval '1 day'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'god_mode_review', 7200, 3600, 0.0516, now() - interval '1 day'),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'research_scoring', 11600, 2400, 0.0468, now()),
  (demo_brand_id, 'anthropic', 'claude-sonnet-4-6', 'content_generation', 7800, 4400, 0.0576, now());

-- ── 11. Calendar events ──────────────────────────────────────────────────────
INSERT INTO calendar_events (brand_id, draft_id, title, event_type, event_status, scheduled_for, created_at)
VALUES
  (demo_brand_id, draft_1, 'LinkedIn: Open-source AI market', 'social', 'published', now() - interval '2 days', now() - interval '2 days'),
  (demo_brand_id, draft_2, 'LinkedIn: HN open-source thread', 'social', 'confirmed', now() + interval '1 day 9 hours', now() - interval '14 hours'),
  (demo_brand_id, draft_6, 'Newsletter #4 — Market map issue', 'newsletter', 'planned', now() + interval '3 days', now() - interval '2 hours'),
  (demo_brand_id, null, 'LinkedIn: GOD Mode architecture', 'social', 'planned', now() + interval '5 days', now()),
  (demo_brand_id, null, 'X Thread: Full pipeline overview', 'social', 'planned', now() + interval '7 days', now()),
  (demo_brand_id, null, 'Blog: Multi-tenancy deep dive', 'blog_video', 'planned', now() + interval '10 days', now());

RAISE NOTICE 'Demo seed completed successfully for brand: ZeroHuman Demo (%)' , demo_brand_id;
END $$;
