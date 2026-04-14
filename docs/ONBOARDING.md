# Brand Onboarding Guide 🚀

Because this platform is designed as an autonomous multi-tenant engine, adding a new client/brand requires **zero code changes**. Everything is handled at the database level.

## 1. Register the Brand
In Supabase, insert a new record into the `brands` table:
- **`name`**: e.g., "Acme Corp"
- **`slug`**: e.g., "acme-corp"
- **`topics`**: Standard tag array (e.g., `["saas", "tech"]`)
- **`tone_of_voice`**: JSON object containing rules, formatting constraints, and personality traits.

## 2. Generate Agent Squad (Automatic)
Thanks to the SQL Migration `005_agent_system.sql`, the moment you create a new brand, the database **automatically** spawns 7 core agents specific to that brand.
You can view or configure them further in the `agent_configs` and `agent_skills` tables.

## 3. Create the Users
Insert authorized users into the `users` table and link them to the newly generated `brand_id`.
Assign one of the roles: `owner`, `editor`, or `viewer`. This natively syncs with Supabase Auth.

## 4. Provide the Dashboard JWT
Once users authenticate via the Next.js frontend, they receive a JWT.
Every API request reaching the Python Backend with `Authorization: Bearer <JWT>` will automatically contextualize operations, LLM prompts, and RLS database queries exclusively for "Acme Corp". 

You're done! The Brand is live.
