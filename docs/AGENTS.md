# Multi-Agent Ecosystem 🤖

The core of the Content Engine is powered by a multi-agent orchestration pattern rather than a simple zero-shot LLM pass. All agents load their identity and instructions dynamically from the platform database based on the active `brand_id`.

## 🗃 The Agent Loader

To avoid hardcoded identities in Python files, the module `python/src/content_engine/agents/agent_loader.py` fetches the raw agent persona during execution using the Supabase JWT.
- **Table:** `agent_configs`
- **Fallback:** If a brand hasn't customized its agent, it falls back to a core System Blueprint heavily optimized via XML structured prompt engineering.

## 👥 The 7 Core Personas

For each brand, the system recognizes these interconnected personas:

1. **Writer**: Focuses on drafting content heavily aligned with the brand's exact tone of voice and source materials.
2. **Editor**: A fastidious agent meant to fix grammar, remove hallucinations, formatting errors, and adapt the piece to the specific layout of the chosen platform (e.g., LinkedIn vs Twitter).
3. **Adapter**: Capable of reading an anchor piece of content and recycling it seamlessly for secondary networks.
4. **GOD Advocate**: First element of the *GOD System*. Plays the devil's advocate, critiquing the draft from a structural and logical standpoint.
5. **GOD Fact-Checker**: Second element of the *GOD System*. Aggressively searches for logical fallacies or fake news within the generated content.
6. **GOD Creative**: Third element of the *GOD System*. Searches for the "spark" — how can this be angled better?
7. **GOD Synthesis**: The final judge. Reads the inputs from the Advocate, Fact-Checker, and Creative, delivering a single unified verdict (`pass`, `needs_revision`, `reject`).

## ⚔️ The Writing Lab (A/B Routing)

Because finding the perfect "hook" is often unpredictable, the system exposes a competitive `writing_lab.py`. 
You can spin up an arena comparing a "Champion" draft against a "Challenger" prompt iteration. The engine evaluates both results analytically, producing a verified winner, which allows empirical improvement of your content across sprints.
