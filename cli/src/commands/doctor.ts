/**
 * zh doctor — Diagnose the ZeroHuman Agency installation.
 */

import chalk from 'chalk'
import { execSync } from 'child_process'
import { existsSync } from 'fs'
import { printLogo, printSection } from '../lib/logo.js'
import { read as readEnv, maskSecret, isSecretKey } from '../lib/env-writer.js'
import { checkSupabase, checkBackend, checkUrl, formatTable, CheckResult } from '../lib/health.js'

const VERSION = '0.1.0'

function checkCommand(cmd: string): string | null {
  try { return execSync(`${cmd} --version 2>&1`, { timeout: 3000 }).toString().trim().split('\n')[0] }
  catch { return null }
}

export async function runDoctor(): Promise<void> {
  printLogo(VERSION)
  console.log(chalk.hex('#f5f0e8').bold('  ZeroHuman Doctor') + '\n')

  const env = readEnv()

  // ── Environment ────────────────────────────────────────────────────────────
  printSection('Environment')

  const envChecks: CheckResult[] = [
    { label: 'Node.js', status: 'ok', detail: process.version },
  ]

  const python = checkCommand('python3') ?? checkCommand('python')
  envChecks.push({ label: 'Python', status: python ? 'ok' : 'warn', detail: python ?? 'not found' })

  const uv = checkCommand('uv')
  envChecks.push({ label: 'uv', status: uv ? 'ok' : 'warn', detail: uv ?? 'not found — install: pip install uv' })

  const docker = checkCommand('docker')
  envChecks.push({ label: 'Docker', status: docker ? 'ok' : 'skip', detail: docker ?? 'not found (optional)' })

  const supabaseCli = checkCommand('supabase')
  envChecks.push({ label: 'Supabase CLI', status: supabaseCli ? 'ok' : 'skip', detail: supabaseCli ?? 'not found (optional)' })

  console.log(formatTable(envChecks))
  console.log()

  // ── Configuration ──────────────────────────────────────────────────────────
  printSection('Configuration (.env.local)')

  const envPath = existsSync(process.cwd() + '/.env.local')
    ? process.cwd() + '/.env.local'
    : null

  if (!envPath) {
    console.log(chalk.hex('#f87171')('  ✗ .env.local not found — run zh init'))
    console.log()
  } else {
    const configChecks: CheckResult[] = []
    const requiredKeys = [
      'NEXT_PUBLIC_SUPABASE_URL',
      'NEXT_PUBLIC_SUPABASE_ANON_KEY',
      'SUPABASE_SERVICE_ROLE_KEY',
      'BRAND_SECRETS_ENCRYPTION_KEY',
      'SCHEDULER_SECRET',
    ]
    const llmKeys = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GOOGLE_AI_API_KEY']

    for (const key of requiredKeys) {
      const val = env[key]
      configChecks.push({
        label: key,
        status: val ? 'ok' : 'fail',
        detail: val ? maskSecret(val) : 'not set',
      })
    }

    const hasLlm = llmKeys.some(k => !!env[k])
    configChecks.push({ label: 'LLM provider', status: hasLlm ? 'ok' : 'fail', detail: hasLlm ? llmKeys.filter(k => env[k]).join(', ').replace(/_API_KEY/g, '').toLowerCase() : 'none configured' })

    const optionalKeys = ['SERPER_API_KEY', 'TAVILY_API_KEY', 'YOUTUBE_API_KEY', 'RESEND_API_KEY', 'REPLICATE_API_TOKEN']
    for (const key of optionalKeys) {
      const val = env[key]
      if (val) {
        configChecks.push({ label: key, status: 'ok', detail: maskSecret(val) })
      }
    }

    console.log(formatTable(configChecks))
    console.log()
  }

  // ── Connections ────────────────────────────────────────────────────────────
  printSection('Connections')

  const connChecks: CheckResult[] = []
  const connPromises: Promise<void>[] = []

  if (env.NEXT_PUBLIC_SUPABASE_URL && env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    connPromises.push(
      checkSupabase(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
        .then(r => { connChecks.push(r) })
    )
  } else {
    connChecks.push({ label: 'Supabase', status: 'skip', detail: 'not configured' })
  }

  const backendUrl = env.PYTHON_BACKEND_URL ?? 'http://localhost:8082'
  connPromises.push(
    checkBackend(backendUrl).then(r => { connChecks.push(r) })
  )

  // Local gateways
  const gateways = [
    { label: 'Ollama (11434)', url: 'http://localhost:11434/api/version' },
    { label: 'LM Studio (1234)', url: 'http://localhost:1234/v1/models' },
    { label: 'OpenClaw (18789)', url: 'http://localhost:18789/v1/models' },
  ]
  for (const gw of gateways) {
    connPromises.push(
      checkUrl(gw.url, 2000).then(r => {
        connChecks.push({ label: gw.label, status: r.ok ? 'ok' : 'skip', detail: r.ok ? 'online' : 'not running', latency_ms: r.latency_ms })
      })
    )
  }

  await Promise.all(connPromises)
  console.log(formatTable(connChecks))
  console.log()

  // ── Overall Verdict ────────────────────────────────────────────────────────
  const critical = ['Supabase DB', 'LLM provider']
  const failures = connChecks.filter(c => c.status === 'fail' && critical.includes(c.label))

  if (failures.length === 0) {
    console.log(chalk.hex('#4ade80')('  ✓ ') + chalk.hex('#f5f0e8').bold('System ready'))
  } else {
    console.log(chalk.hex('#f87171')('  ✗ ') + chalk.hex('#f5f0e8').bold(`${failures.length} critical issue(s) found`))
    console.log()
    for (const f of failures) {
      console.log(chalk.hex('#555')(`    → Fix: ${f.label} — ${f.detail}`))
    }
    console.log()
    console.log(chalk.hex('#555')('  Run: ') + chalk.hex('#f5f0e8')('zh init') + chalk.hex('#555')(' to reconfigure'))
  }
  console.log()
}
