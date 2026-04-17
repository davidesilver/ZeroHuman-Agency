# Content Engine Operator Runbook

## 1. System Overview
The Content Engine AI system runs asynchronously using highly parallel LLM calls, robust LLM rate limits, and fallback strategies. The dashboard provides real-time observability of engine uptime, queue size, API spend, and model latency.

## 2. Alerts and Responses

### Alert: "Emergency Fallback Triggered"
**Symptom**: Anthropic API goes down or denies the request (e.g. 429 or 503). System falls back to OpenRouter.
**Action**:
1. Check dashboard LLM Observability cards. Notice if fallback continues to rise.
2. The AI system will self-heal by switching to free models.
3. Once the primary APIs recover, the circuit breakers (`llm_client.py`) will reinstate the primary connections.

### Alert: "Total Pipeline Errors > 0"
**Symptom**: Unrecoverable JSON parsing or routing bugs.
**Action**:
1. Check the queue size. If the errors are localized to 1 task, let it fail.
2. Use the database `god_mode_reviews` table for direct inspection. 

## 3. Routine Operations
- **System Health Check**: Visit `/dashboard` to view KPI cards (Avg Uptime, Total Errors, total Queue).
- **Cost Inspection**: Verified in the `API spend today` widget on the dashboard.
- **Brand Rules**: The agents evaluate according to specific brand requirements in the `settings` and `agents` sections.

*(Generated automatically by the AI meta-orchestration agent)*
