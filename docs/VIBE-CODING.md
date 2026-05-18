# Vibe Coding Guide

> **For non-developers.** This guide teaches you how to use Claude Code to customize, configure, and extend ZeroHuman Agency by describing what you want in plain language — no coding required.

---

## What is vibe coding?

Vibe coding means telling an AI assistant (Claude Code) what you want the platform to do, and letting it write the code, apply the configuration, and verify the result. You describe the outcome; Claude handles the implementation.

**You need:**
- Claude Code installed (`npm install -g @anthropic-ai/claude-code` or via the Claude desktop app)
- The repo cloned locally
- Access to the `.env.local` file

**You don't need:**
- Knowledge of TypeScript, Python, or SQL
- Understanding of the API structure
- Experience with git

---

## Getting started

Open a terminal in the project folder and run:

```bash
claude
```

Claude Code will load the project context, read the skills pinned in `skills-lock.json`, and be ready to help. From this point on, just describe what you want.

---

## Common tasks — what to say

### Activate a feature for your brand

> "Enable deep research for my brand. The brand ID is `abc-123`."

> "Turn on email marketing (Brevo) for the brand called Acme Corp."

> "Activate video generation for all brands."

Claude will write the SQL or API call, apply the feature flag, and confirm the change.

---

### Add a Brevo API key (email marketing)

> "Save my Brevo API key `xkeysib-abc123` for brand Acme Corp."

> "Set up Brevo for our brand. The API key is in the .env file as BREVO_KEY."

Claude will store the key encrypted in `brand_integrations` via the secure secrets API. The key is never stored in plain text.

---

### Add competitor URLs to monitor

> "Start monitoring these competitor pages: `https://competitor.com/blog` and `https://competitor.com/pricing`."

> "Add a new competitor URL for our brand: `https://rival.io/features`."

Claude will call the competitor snapshot API and set up periodic monitoring.

---

### Start a deep research job

> "Research 'AI trends in B2B SaaS marketing 2026' at depth 3."

> "Do a quick research (depth 1) on 'email automation tools comparison'."

Results will appear in the **Deep Research** page and feed automatically into the ideation pipeline.

---

### Change brand voice and tone

> "Update our brand tone. We want to sound confident but not arrogant, use simple words, avoid buzzwords, and always speak to mid-market operations managers."

> "Add 'supply chain' and 'warehouse automation' to the topics for brand Acme Corp."

> "Set our founder principles: we never mention competitors by name, we always include data from primary sources, and every post ends with a practical takeaway."

Claude will update the `brands` table directly via the settings API.

---

### Add RSS sources for research

> "Add these RSS feeds to our research sources: `https://feedburner.com/example` (label: 'Industry Blog') and `https://techcrunch.com/feed` (label: 'Tech News')."

---

### Customize an AI agent's personality

> "Rewrite the writer agent for our brand. It should write like a senior B2B analyst: data-driven, no fluff, structured arguments, bullet points only when comparing options."

> "Make the editor agent stricter — it should flag any sentence longer than 25 words and any use of passive voice."

Claude will update the agent configuration in Settings → Agents.

---

### Set daily LLM spending cap

> "Set the daily budget for Acme Corp to $5."

> "Increase the global LLM daily cap to $20."

---

### Upload brand assets

> "Upload our logo and brand palette PDF to the brand assets."

Claude will guide you through the upload or do it via the Supabase Storage API.

---

### Generate content ideas from a research result

> "Take the research job about AI marketing trends and generate 5 LinkedIn post ideas from it."

> "Turn the latest deep research results into a content brief."

---

### Create a video from a template

> "Render a Weekly Recap video for the week starting 2026-05-12. Headline: 'AI Takes Over Content Marketing'. Highlight: '3 campaigns launched, 40% engagement increase'."

Results appear in the **Videos** page. Output is stored in Supabase Storage.

---

### Check what's consuming LLM budget

> "Show me the LLM spending breakdown for the last 7 days by provider."

> "Which provider is cheapest per 1k tokens based on our usage?"

---

### Add a new user to a brand

> "Add user `alice@example.com` to brand Acme Corp as an editor."

> "Create a new brand called 'Beta Client' and assign it to `newuser@example.com`."

---

## What Claude can and cannot do

| Can do | Cannot do |
|---|---|
| Enable/disable feature flags | Access your personal passwords |
| Set encrypted brand secrets | Read secrets after they are stored |
| Update brand voice and topics | Push code to GitHub without your approval |
| Start research jobs and render videos | Send emails or publish posts without asking |
| Add users and create brands | Delete data permanently without confirmation |
| Customize agent prompts | Override Supabase Row Level Security |
| Apply database migrations | Access other users' data |

If Claude is about to do something irreversible (delete data, publish publicly, send an email), it will always ask for your explicit confirmation first.

---

## Tips for good vibe coding

**Be specific about the brand.**
> ✅ "For brand Acme Corp..."
> ❌ "For our brand..." (ambiguous if you have multiple brands)

**Describe the outcome, not the steps.**
> ✅ "I want the writer agent to sound more conversational."
> ❌ "Change the `writer_prompt` field in the `agent_configs` table to include..."

**Give Claude permission to check first.**
> "Check what feature flags are currently enabled for Acme Corp, then enable competitor monitoring if it's not already on."

**Ask for a dry run on risky operations.**
> "Show me what you would change before actually doing it."

**Iterate naturally.**
> "That's good, but also add a note that we never use em-dashes."
> "Revert that last change."

---

## Settings you can change without code

Everything in the Settings section of the dashboard can be managed through conversation:

| Setting | Page | Ask Claude |
|---|---|---|
| Brand topics and tone | Settings → Brand Context | "Update our topics and tone" |
| RSS/research sources | Settings → Brand Context | "Add this RSS feed" |
| Brevo API key | Settings → Audience | "Save my Brevo key" |
| Agent personalities | Settings → Agents | "Rewrite the writer agent" |
| Social connections | Settings → Social | "Connect our LinkedIn account" |
| Feature flags | Settings → Feature Flags | "Enable video for this brand" |
| Video templates | Settings → Video Templates | "Create a new template called..." |
| Email automations | Settings → Automations | "Create a welcome sequence" |
| Daily budget | Settings → Brand Context | "Set the daily budget to $5" |
| Image generation | Settings → Image Generation | "Switch to Replicate with FLUX" |

---

## Troubleshooting via vibe coding

**Something broke? Just say:**
> "The deep research page is showing an error. What's wrong?"

> "The competitor monitoring feature is not enabled for my brand. Fix it."

> "I can't see the Videos page in the sidebar. Something's missing."

**Need to understand a setting?**
> "What does the scoring weight for 'applicability' actually do?"

> "Explain what depth 5 means for deep research jobs."

**Want to know what's configured?**
> "Show me all the feature flags for brand Acme Corp."

> "What Brevo lists do we have connected?"

> "What agents are customized for this brand?"

---

## What vibe coding cannot replace

Some tasks still require a developer or system administrator:

- Initial server/infrastructure setup (first-time deploy to Vercel/Railway)
- Supabase project creation and CLI setup
- DNS and domain configuration
- Generating the `BRAND_SECRETS_ENCRYPTION_KEY` (run once, store safely)
- Setting up Postiz OAuth apps on LinkedIn/X/Meta developer consoles
- Major schema migrations after production launch

For these, refer to [`docs/SETUP.md`](SETUP.md) and [`docs/DEPLOYMENT.md`](DEPLOYMENT.md), or ask your technical contact.

---

## Quick reference card

```
"Enable [feature] for brand [name]"
"Set my [service] API key to [key]"
"Monitor competitor [url]"
"Research [topic] at depth [1-5]"
"Update brand tone: [description]"
"Add [user] as [role] to brand [name]"
"Show me [metric] for the last [period]"
"Render a [template name] video with [variables]"
"Generate [n] content ideas from the latest research"
"What's currently configured for brand [name]?"
```

---

*For the full technical reference, see [`docs/SETUP.md`](SETUP.md), [`docs/API.md`](API.md), and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).*
