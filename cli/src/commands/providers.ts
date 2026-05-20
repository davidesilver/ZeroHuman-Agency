import chalk from 'chalk'
import * as p from '@clack/prompts'
import { printSection, ok, fail, info } from '../lib/logo.js'
import { read as readEnv, write as writeEnv, maskSecret } from '../lib/env-writer.js'

const CATALOG = [
  { id: 'anthropic', label: 'Anthropic Claude', envKey: 'ANTHROPIC_API_KEY', prefix: 'sk-ant-', baseUrl: 'https://api.anthropic.com/v1', type: 'anthropic' },
  { id: 'openai', label: 'OpenAI', envKey: 'OPENAI_API_KEY', prefix: 'sk-', baseUrl: 'https://api.openai.com/v1', type: 'openai' },
  { id: 'groq', label: 'Groq', envKey: 'GROQ_API_KEY', prefix: 'gsk_', baseUrl: 'https://api.groq.com/openai/v1', type: 'openai' },
  { id: 'openrouter', label: 'OpenRouter', envKey: 'OPENROUTER_API_KEY', prefix: 'sk-or-', baseUrl: 'https://openrouter.ai/api/v1', type: 'openai' },
  { id: 'google', label: 'Google AI (Gemini)', envKey: 'GOOGLE_AI_API_KEY', prefix: 'AI', baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', type: 'openai' },
  { id: 'deepseek', label: 'DeepSeek', envKey: 'DEEPSEEK_API_KEY', prefix: 'sk-', baseUrl: 'https://api.deepseek.com/v1', type: 'openai' },
  { id: 'mistral', label: 'Mistral AI', envKey: 'MISTRAL_API_KEY', prefix: '', baseUrl: 'https://api.mistral.ai/v1', type: 'openai' },
  { id: 'xai', label: 'xAI (Grok)', envKey: 'XAI_API_KEY', prefix: 'xai-', baseUrl: 'https://api.x.ai/v1', type: 'openai' },
  { id: 'together', label: 'Together AI', envKey: 'TOGETHER_API_KEY', prefix: '', baseUrl: 'https://api.together.xyz/v1', type: 'openai' },
  { id: 'groq_free', label: 'Groq (free tier)', envKey: 'GROQ_API_KEY', prefix: 'gsk_', baseUrl: 'https://api.groq.com/openai/v1', type: 'openai' },
  { id: 'cerebras', label: 'Cerebras', envKey: 'CEREBRAS_API_KEY', prefix: '', baseUrl: 'https://api.cerebras.ai/v1', type: 'openai' },
  { id: 'sambanova', label: 'SambaNova', envKey: 'SAMBANOVA_API_KEY', prefix: '', baseUrl: 'https://api.sambanova.ai/v1', type: 'openai' },
  { id: 'perplexity', label: 'Perplexity', envKey: 'PERPLEXITY_API_KEY', prefix: 'pplx-', baseUrl: 'https://api.perplexity.ai', type: 'openai' },
]

async function testKey(provider: (typeof CATALOG)[0], key: string): Promise<{ ok: boolean; models?: string[]; latency_ms: number }> {
  const t0 = Date.now()
  try {
    const headers: Record<string, string> = provider.type === 'anthropic'
      ? { 'x-api-key': key, 'anthropic-version': '2023-06-01' }
      : { Authorization: `Bearer ${key}` }
    const res = await fetch(`${provider.baseUrl}/models`, { headers, signal: AbortSignal.timeout(8000) })
    const latency_ms = Date.now() - t0
    if (!res.ok) return { ok: false, latency_ms }
    const data = await res.json() as { data?: Array<{ id: string }> }
    return { ok: true, models: data.data?.slice(0, 5).map(m => m.id) ?? [], latency_ms }
  } catch {
    return { ok: false, latency_ms: Date.now() - t0 }
  }
}

export async function runProvidersList(): Promise<void> {
  printSection('LLM Providers')
  const env = readEnv()
  const seen = new Set<string>()
  for (const prov of CATALOG) {
    if (seen.has(prov.envKey)) continue
    seen.add(prov.envKey)
    const val = env[prov.envKey]
    const status = val ? chalk.hex('#4ade80')('✓ configured') : chalk.hex('#555')('○ not set')
    const masked = val ? chalk.hex('#888')(maskSecret(val)) : ''
    console.log(`  ${status}  ${chalk.hex('#f5f0e8')(prov.label.padEnd(24))} ${masked}`)
  }
  console.log()
}

export async function runProvidersAdd(id?: string): Promise<void> {
  printSection('Add Provider')
  let prov = id ? CATALOG.find(p => p.id === id) : undefined
  if (!prov) {
    const sel = await p.select({
      message: 'Select provider to configure',
      options: CATALOG.map(p => ({ value: p.id, label: p.label })),
    })
    if (p.isCancel(sel)) { process.exit(0) }
    prov = CATALOG.find(c => c.id === sel)!
  }

  const key = await p.text({ message: `${prov.label} API key`, placeholder: prov.prefix + '...' })
  if (p.isCancel(key)) { process.exit(0) }

  const spinner = p.spinner()
  spinner.start('Validating key...')
  const result = await testKey(prov, key as string)
  spinner.stop(result.ok ? 'Key validated' : 'Validation failed')

  if (result.ok) {
    ok(`${prov.label} — ${result.latency_ms}ms — ${result.models?.join(', ')}`)
    writeEnv({ [prov.envKey]: key as string })
    ok('Saved to .env.local')
  } else {
    fail('Key validation failed — check the key and try again')
    process.exit(1)
  }
}

export async function runProvidersTest(id: string): Promise<void> {
  const env = readEnv()
  const prov = CATALOG.find(p => p.id === id)
  if (!prov) { fail(`Unknown provider: ${id}`); process.exit(1) }
  const key = env[prov.envKey]
  if (!key) { fail(`No key configured for ${prov.label} — run zh providers add ${id}`); process.exit(1) }
  info(`Testing ${prov.label}...`)
  const result = await testKey(prov, key)
  if (result.ok) {
    ok(`${prov.label} — ${result.latency_ms}ms — ${result.models?.join(', ')}`)
  } else {
    fail(`${prov.label} — connection failed`)
    process.exit(1)
  }
}

export async function runProvidersRemove(id: string): Promise<void> {
  const prov = CATALOG.find(p => p.id === id)
  if (!prov) { fail(`Unknown provider: ${id}`); process.exit(1) }
  const confirm = await p.confirm({ message: `Remove ${prov.label} key from .env.local?` })
  if (!confirm || p.isCancel(confirm)) { process.exit(0) }
  const env = readEnv()
  delete env[prov.envKey]
  const { write } = await import('../lib/env-writer.js')
  write(env)
  ok(`${prov.label} key removed`)
}
