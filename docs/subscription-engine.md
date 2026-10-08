# Local subscription engine

The text engine supports `LLM_MODE=api` (backward-compatible default) and
`LLM_MODE=codex_subscription` (official Codex CLI with ChatGPT authentication).

## Setup

Install the official CLI using the [OpenAI instructions](https://developers.openai.com/codex/cli),
then run `codex login` as the OS user running the Python backend. The integration
was validated with Codex 0.160.1. It requires support for `--strict-config`,
`--ignore-user-config`, `--ignore-rules` and the feature switches used in the runner.
Older incompatible versions fail rather than weakening these settings.

Set these in the repository's private `.env.local` and restart the backend:

```dotenv
LLM_MODE=codex_subscription
CODEX_MODEL=
CODEX_TIMEOUT_SECONDS=180
```

Blank `CODEX_MODEL` selects the official CLI default, reported as `codex-default`.
An explicit model must be a Codex model, not an OpenRouter model identifier.
Temperature and per-task API-model selection do not apply in this mode.
Run the backend from `python/`, matching the existing `../.env.local` loader.
Containers do not inherit the host login; this mode currently targets native execution.

## Routing and failure behavior

Subscription mode overrides paid BYOK choices in the provider registrar and handles
the central `call_llm` entry plus the humanizer's explicit-model path. Quota,
login, timeout and CLI failures propagate without API fallback. Existing JSON
parsing continues to apply. Responses report CLI usage and unknown monetary cost
(`None`); subscription allowances are not an API-dollar budget.

Each invocation uses a temporary working directory, stdin for prompts, ephemeral
sessions and a minimal environment. It does not load personal Codex configuration
or project instruction files, and forces ChatGPT authentication. Shell, browser,
image tools, apps, plugins, hooks and delegation are disabled. Unexpected tool
completion events or ignored-config diagnostics reject the response. Cancellation
and timeout terminate/reap the child process. The CLI still uses its own login
storage; the adapter never extracts or copies tokens.

Use this only as an owner-operated local deployment. All brands share the logged-in
owner's subscription. This is not a per-tenant login flow. A separately distributed
application should implement the official [Sign in with ChatGPT integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)
with its own registration/session lifecycle.

## Data and optional services

Keep Supabase for this iteration: the app relies on its clients, authentication,
RLS and storage, so SQLite or Neon are not connection-string replacements.
SQLite is reasonable for a separate local queue/cache; replacing the entire data
layer requires a migration design. Neon can host PostgreSQL, but the existing
PostgREST calls and auth/storage dependencies still need conversion.

Clerk is unnecessary while Supabase Auth remains. Resend is already optional
newsletter delivery. Cloudflare hosting/storage should be added only for an actual
deployment or asset-delivery requirement. No new external services are provisioned.

This change converts text inference, not image generation, embedding APIs,
research, email or social publication. Higgsfield media and Postiz publishing
remain separate integrations. A live text smoke test does not establish complete
engine readiness or authorize social posting.

## Verification

From `python/`: `uv run pytest tests/test_codex_subscription.py -q`.
Tests cover routing, failures, process cleanup and API-key isolation.
The live acceptance test uses fictional JSON and consumes only ChatGPT plan usage.
