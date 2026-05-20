# Content #3 — Why Open Source (launch piece)

## LinkedIn version

I just open-sourced a platform that took 6 months to build. MIT license. No strings.

ZeroHuman is an AI content engine that automates the full lifecycle: research, scoring, drafting, multi-agent review, humanization, and publishing. It handles multiple brands from one instance.

50+ database tables. 90+ API routes. A Python backend with 10 content retrievers, a scoring engine, 4-agent review, and a content humanizer. A Next.js dashboard. Docker support. Multi-tenant architecture with encrypted per-brand credentials.

Why give it away?

Three reasons:

1. The AI content tool market is full of $49/month SaaS products that do one thing. The ones that do everything cost $500+/month and lock you in. An open-source alternative that you own and host yourself doesn't exist yet. I wanted it to.

2. I can't test this alone. A content engine needs real brands, real audiences, real publishing schedules. I need people using it, breaking it, telling me what matters. That feedback is worth more than any license fee.

3. The best infrastructure is open. Supabase, PostHog, Cal.com — the tools I rely on every day are open-source. I want to be part of that ecosystem, not compete against it.

What ZeroHuman does:
→ Pulls from RSS, search APIs, YouTube, competitors — scores everything
→ Generates platform-native content (LinkedIn, X, blog, newsletter)
→ 4-agent GOD Mode review (critic, fact-checker, creative, synthesis)
→ Strips AI patterns and re-applies your brand voice
→ Publishes or schedules to social channels
→ Feeds engagement metrics back into content scoring

Tech stack: Next.js 16 + Python FastAPI + Supabase + Docker

If you run a marketing agency or manage content for multiple brands, this was built for you. Every table has row-level security per brand. Your clients' data never touches each other.

Star it, try it, break it, tell me what's wrong:
https://github.com/davidesilver/ZeroHuman-Agency

#OpenSource #AI #ContentMarketing #BuildInPublic

---

## X (Twitter) version — thread

🧵 I just open-sourced a platform that took 6 months to build. MIT license. Here's what it does and why I gave it away.

1/ ZeroHuman is an AI content engine. Full lifecycle:

Research → Scoring → Draft → 4-Agent Review → Humanize → Publish

Multiple brands from one instance. 50+ DB tables. 90+ API routes.

2/ What it actually does:
- Pulls from RSS, search APIs, YouTube, competitors
- Scores everything (relevance, credibility, trend signal)
- Generates platform-native content (LinkedIn, X, blog, newsletter)
- 4-agent review system (GOD Mode)
- Strips AI patterns, applies YOUR voice
- Publishes to social channels
- Engagement metrics feed back into scoring

3/ Why open source?

The market has $49/mo tools that do one thing, and $500+/mo platforms that lock you in.

An open-source alternative you own and host? Didn't exist.

4/ I can't test this alone. A content engine needs real brands, real audiences.

Your feedback > any license fee.

5/ Built for agencies: every table has row-level security per brand. Your clients' data never touches each other. Encrypted credentials per brand.

Stack: Next.js 16 + Python FastAPI + Supabase + Docker

⭐ https://github.com/davidesilver/ZeroHuman-Agency
