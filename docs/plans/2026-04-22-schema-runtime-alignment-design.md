# Schema/Runtime Alignment Design

Date: 2026-04-22
Role: `plan-eng-review`
Status: Proposed

## Goal

Bring the repository back to a coherent, deployable state where:

- Supabase migrations, generated TS types, and Python/Next.js runtime contracts agree
- multi-brand routing works end-to-end, not only at the UI layer
- retrievers, scheduler, newsletter, and analytics operate against the real schema
- legacy compatibility is explicit, temporary, and testable

This design is based on direct repo inspection plus reconciliation of two competing analyses:

- the broad architectural map was directionally correct
- the immediate operational priority must follow the actual code paths that break today

## Current Reality

The repo is not broken in one place. It is broken at the contract boundaries:

1. Python retriever models and DB enums are out of sync.
2. Next.js proxying does not reliably propagate the active brand to the Python backend.
3. Generated TS types do not reflect the latest migration set present in the repo.
4. Scheduler and analytics still contain single-brand and stale-schema assumptions.
5. `users.brand_id` is in an unsafe transitional state: dropped by one migration, still referenced by code and generated contracts.

The key correction to earlier planning is priority:

- the first change must unblock runtime behavior now
- schema cleanup follows only after the runtime contract is stabilized

## Non-Goals

- No redesign of the product workflow
- No refactor of agent prompting strategy
- No redesign of the memory layer
- No destructive schema cleanup in the first PR

## Design Principles

### 1. Migrations are the source of truth

`supabase/migrations` defines the data contract. Runtime code must adapt to it, or the migration plan must be corrected explicitly. Comments and stale generated files are not authoritative.

### 2. No ghost compatibility

If a fallback exists, it must be:

- intentional
- documented
- test-covered
- scheduled for removal

Temporary compatibility that is not verified is treated as debt, not safety.

### 3. Additive before destructive

Any destructive cleanup, especially around `users.brand_id`, happens only after all runtime call sites and generated contracts are removed.

### 4. Separate concepts must stay separate

`retriever_type` and `source_type` are different dimensions:

- `retriever_type`: how the item entered the system
- `source_type`: what kind of source/content it is

They must not be collapsed into one enum.

### 5. Multi-brand must be explicit

The active brand has to be carried across every boundary:

- browser state
- Next.js route handlers
- proxy layer
- Python middleware
- DB access

Silently falling back to "first brand" is allowed only as a temporary compatibility path and must never override an explicitly selected active brand.

## Root Cause Breakdown

## A. Retriever contract drift

Observed mismatch:

- Python `RetrieverType` and `SourceType` are not aligned with the DB contract used by the pipeline.
- Some retrievers use legacy enum values, others use ad-hoc string sentinels.
- The runtime currently mixes three states:
  - old enum vocabulary
  - partially migrated new vocabulary
  - suppressed type errors

Impact:

- new retrievers can be skipped or fail model validation
- persisted `research_items` rows can violate DB enum expectations
- the orchestrator is not trustworthy as the contract boundary for ingestion

## B. Multi-brand propagation gap

Observed mismatch:

- the UI stores an active brand and server-side auth resolves it
- the Python backend accepts `X-Brand-ID`
- the proxy helper does not consistently forward the active brand

Impact:

- multi-brand looks functional in UI but backend work can still target the default membership brand
- research, scoring, generation, memory, and writing-lab can all operate on the wrong tenant

## C. Generated contract drift

Observed mismatch:

- `src/lib/types/database.types.ts` still models dropped or stale fields and enum values

Impact:

- TS code can typecheck against a schema that no longer matches the migrations
- generated contracts stop being useful as a safety rail

## D. Scheduler and analytics drift

Observed mismatch:

- daily scheduler logic remains single-brand in key places
- analytics code assumes columns or semantics that are not stable in the current schema
- `social_metrics` write behavior is not aligned with the uniqueness model

Impact:

- repeated runs can fail or overwrite with unclear semantics
- scheduled automation is not safe to trust in production

## E. Unsafe `users.brand_id` transition

Observed mismatch:

- one migration attempts to drop it
- multiple runtime and generated paths still assume it exists

Impact:

- fresh install, partial migration state, or future cleanup can break auth/bootstrap paths
- the repo does not currently express a single safe state

## Decisions

### Decision 1: Fix runtime before cleanup

We will not start with destructive schema cleanup. We will first restore a valid runtime contract.

Why:

- runtime retriever failures and tenant-routing failures are user-visible today
- destructive cleanup without eliminating live call sites increases risk

### Decision 2: Introduce a transitional canonical contract for ingestion

The implementation plan will explicitly define:

- canonical `retriever_type`
- canonical `source_type`
- which old values are temporarily accepted
- where mapping happens

Recommended shape:

- `retriever_type` remains the technical ingestion channel
- `source_type` remains the content/source classification
- if UI needs user-friendly labels, map in code or a lookup object, not by overloading DB enums

### Decision 3: Treat `users.brand_id` as deprecated-but-not-removable until proven unused

Even if some environment already applied a drop, the repository is not ready to treat that as complete. The plan must first remove all runtime dependencies and only then schedule final deletion.

### Decision 4: Scheduler must converge on explicit multi-brand orchestration

We will remove ambiguous single-brand assumptions from cron-triggered paths. A job either:

- loops through all eligible brands
- or takes a specific brand explicitly

No hidden global-brand behavior except temporary dev fallback.

## Delivery Plan

## PR1: `runtime-unblock`

Purpose: restore correct runtime behavior with minimal destructive change.

Scope:

- align Python model enums with the ingestion contract actually used by the DB and retrievers
- remove ad-hoc sentinel enum values from retrievers
- fix `proxyToBackend()` to forward active brand context via `X-Brand-ID`
- verify all proxied Python-facing routes inherit the same behavior
- add tests for:
  - retriever model validation
  - brand header propagation
  - `403` on non-member brand selection

Success criteria:

- retrievers no longer fail due to enum mismatch
- switching brand in UI changes the brand used by proxied Python endpoints
- no schema-destructive changes in this PR

Risks:

- accidentally locking the repo into the wrong enum vocabulary

Mitigation:

- keep the PR focused on runtime correctness plus explicit contract notes

## PR2: `schema-contract-stabilization`

Purpose: make migrations, runtime code, and generated types agree.

Scope:

- write a corrective migration that stabilizes the schema without unsafe drops
- audit and remove residual `users.brand_id` runtime dependencies
- update bootstrap/auth fallback paths to use membership-based logic only where safe
- regenerate `src/lib/types/database.types.ts`
- update documentation that claims stale contracts

Success criteria:

- fresh bootstrap from migrations produces the schema the app actually expects
- generated TS types match the migration set
- no required runtime path depends on `users.brand_id`

Risks:

- accidental breakage in brand bootstrap or legacy local environments

Mitigation:

- add compatibility checks and smoke tests for brand creation and first-login flows

## PR3: `scheduler-analytics-cleanup`

Purpose: make automation and metrics predictable in multi-brand operation.

Scope:

- move daily pipeline to explicit multi-brand orchestration
- align weekly newsletter and publish-scheduled jobs with the same rule set
- fix `social_metrics` persistence semantics
- remove stale analytics assumptions such as nonexistent schema fields
- add idempotency and repeated-run tests

Success criteria:

- repeated scheduler runs do not create uniqueness failures
- jobs process the intended set of brands deterministically
- analytics no longer depends on ghost columns or ambiguous write behavior

Risks:

- cron logic can be correct in code but misconfigured operationally

Mitigation:

- include a deploy checklist with dry-run verification steps

## Work Breakdown

## Phase 1: Runtime audit and contract freeze

- inventory all `retriever_type` writers
- inventory all `source_type` writers
- inventory all brand-proxied Next.js routes
- inventory all live `users.brand_id` reads and writes
- freeze the target contract in a short compatibility matrix

Output:

- a table of "current value", "target value", "temporary compatibility rule"

## Phase 2: Multi-brand transport fix

- update proxy helper
- verify active brand resolution on all proxied routes
- add focused auth tests

Output:

- end-to-end tenant routing correctness

## Phase 3: Ingestion contract fix

- repair Python models
- repair retrievers
- repair orchestrator assumptions

Output:

- ingest path that can write valid rows consistently

## Phase 4: Schema and generated type alignment

- corrective migration
- generated types refresh
- TS compile sanity

Output:

- one coherent schema contract

## Phase 5: Scheduler and analytics alignment

- job fan-out strategy
- `social_metrics` write semantics
- repeated-run safety

Output:

- production-safe automation behavior

## Test Strategy

### Contract tests

- Python model validation for retriever payloads
- route-level tests for active brand forwarding
- DB-facing tests for enum compatibility

### Integration tests

- user with two brand memberships
- switch active brand and trigger:
  - research
  - scoring
  - newsletter generate
  - memory mutation
  - writing-lab vote

Expected:

- all operations hit the selected brand only

### Scheduler tests

- repeated metrics ingest for same `(draft_id, platform)`
- repeated daily pipeline run
- weekly newsletter over multiple brands

Expected:

- no unique violations
- deterministic per-brand results

### Fresh bootstrap test

- apply migrations from zero
- generate types
- run backend/frontend smoke tests

Expected:

- no contract mismatch on a clean environment

## Rollout Strategy

1. Land PR1 and validate runtime behavior locally.
2. Land PR2 and run fresh-schema bootstrap validation.
3. Land PR3 and validate scheduler/analytics in dry-run mode before enabling production cron.

Do not reorder PR2 and PR3. Scheduler work on top of an unstable schema contract will create misleading results.

## Risks and Mitigations

### Risk: partial environments already drifted from repo migrations

Mitigation:

- compare production/staging schema before applying corrective migrations
- prefer additive corrective migrations over editing history

### Risk: silent tenant leakage during transition

Mitigation:

- explicit `X-Brand-ID` propagation
- negative membership tests
- route-level assertions on selected brand

### Risk: enum churn causes data inconsistency

Mitigation:

- freeze target enum vocabulary before touching retrievers
- document mappings in code comments and tests

## Definition of Done

- runtime retrievers use values valid for the DB contract
- the active brand is propagated from UI through Python backend consistently
- generated TS types match the actual migration set
- no required runtime path depends on `users.brand_id`
- scheduler and analytics run repeatedly without schema or uniqueness failures
- a fresh environment bootstraps cleanly from the repo

## Immediate Next Step

Convert this design into an implementation plan with task order, file list, and verification commands for PR1, PR2, and PR3.
