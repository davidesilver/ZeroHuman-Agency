/**
 * Health check utilities for zh doctor and zh init.
 */

import { execSync } from 'child_process'

export interface CheckResult {
  label: string
  status: 'ok' | 'fail' | 'warn' | 'skip'
  detail: string
  latency_ms?: number
}

export function checkCommand(cmd: string): string | null {
  try {
    return execSync(`${cmd} --version 2>&1`, { timeout: 5000 }).toString().trim().split('\n')[0]
  } catch {
    return null
  }
}

export async function checkUrl(url: string, timeoutMs = 5000): Promise<{ ok: boolean; latency_ms: number; error?: string }> {
  const t0 = Date.now()
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const res = await fetch(url, { signal: controller.signal })
    clearTimeout(timer)
    return { ok: res.ok, latency_ms: Date.now() - t0 }
  } catch (err: unknown) {
    return { ok: false, latency_ms: Date.now() - t0, error: String(err) }
  }
}

export async function checkSupabase(url: string, anonKey: string): Promise<CheckResult> {
  const t0 = Date.now()
  try {
    const res = await fetch(`${url}/rest/v1/`, {
      headers: { apikey: anonKey, Authorization: `Bearer ${anonKey}` },
      signal: AbortSignal.timeout(5000),
    })
    const latency_ms = Date.now() - t0
    if (res.ok || res.status === 200 || res.status === 400) {
      return { label: 'Supabase DB', status: 'ok', detail: `Connected`, latency_ms }
    }
    return { label: 'Supabase DB', status: 'fail', detail: `HTTP ${res.status}`, latency_ms }
  } catch (err: unknown) {
    return { label: 'Supabase DB', status: 'fail', detail: String(err), latency_ms: Date.now() - t0 }
  }
}

export async function checkBackend(backendUrl: string): Promise<CheckResult> {
  const result = await checkUrl(`${backendUrl}/health`)
  return {
    label: 'Python backend',
    status: result.ok ? 'ok' : 'fail',
    detail: result.ok ? 'Healthy' : (result.error ?? 'Unreachable'),
    latency_ms: result.latency_ms,
  }
}

export async function checkLlmProvider(provider: string, baseUrl: string, apiKey: string): Promise<CheckResult> {
  const t0 = Date.now()
  try {
    const res = await fetch(`${baseUrl}/models`, {
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(8000),
    })
    const latency_ms = Date.now() - t0
    if (res.ok) {
      const data = await res.json() as { data?: unknown[] }
      const count = data.data?.length ?? 0
      return { label: provider, status: 'ok', detail: `${count} models`, latency_ms }
    }
    return { label: provider, status: 'fail', detail: `HTTP ${res.status}`, latency_ms }
  } catch (err: unknown) {
    return { label: provider, status: 'fail', detail: String(err), latency_ms: Date.now() - t0 }
  }
}

export function formatTable(rows: CheckResult[]): string {
  const lines: string[] = []
  for (const r of rows) {
    const icon = r.status === 'ok' ? '✓' : r.status === 'fail' ? '✗' : r.status === 'warn' ? '⚠' : '○'
    const latency = r.latency_ms !== undefined ? ` (${r.latency_ms}ms)` : ''
    const label = r.label.padEnd(22)
    lines.push(`  ${icon} ${label} ${r.detail}${latency}`)
  }
  return lines.join('\n')
}
