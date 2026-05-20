/**
 * zh init — Full interactive setup wizard.
 *
 * Steps:
 *  1. Environment detection
 *  2. Supabase credentials
 *  3. LLM provider (at least 1)
 *  4. Auto-generate encryption keys
 *  5. Optional services
 *  6. Preview + write .env.local
 *  7. Run migrations + seed
 *  8. Health check
 */

import * as p from '@clack/prompts'
import chalk from 'chalk'
import { execSync, spawnSync } from 'child_process'
import crypto from 'crypto'
import { printLogo, printSection, ok, fail, info, warn } from '../lib/logo.js'
import { read as readEnv, write as writeEnv, maskSecret } from '../lib/env-writer.js'
import { checkSupabase, checkUrl, checkBackend, formatTable, CheckResult } from '../lib/health.js'

const VERSION = '0.1.0'

// LLM providers known to zh init
const INIT_PROVIDERS = [
  { id: 'anthropic', label: 'Anthropic Claude', prefix: 'sk-ant-', baseUrl: 'https://api.anthropic.com/v1', type: 'anthropic' },
  { id: 'openai', label: 'OpenAI', prefix: 'sk-', baseUrl: 'https://api.openai.com/v1', type: 'openai' },
  { id: 'groq', label: 'Groq (free tier)', prefix: 'gsk_', baseUrl: 'https://api.groq.com/openai/v1', type: 'openai' },
  { id: 'openrouter', label: 'OpenRouter (200+ models)', prefix: 'sk-or-', baseUrl: 'https://openrouter.ai/api/v1', type: 'openai' },
  { id: 'google', label: 'Google AI (Gemini)', prefix: 'AI', baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', type: 'openai' },
  { id: 'deepseek', label: 'DeepSeek', prefix: 'sk-', baseUrl: 'https://api.deepseek.com/v1', type: 'openai' },
]

const ENV_KEY_FOR_PROVIDER: Record<string, string> = {
  anthropic: 'ANTHROPIC_API_KEY',
  openai: 'OPENAI_API_KEY',
  groq: 'GROQ_API_KEY',
  openrouter: 'OPENROUTER_API_KEY',
  google: 'GOOGLE_AI_API_KEY',
  deepseek: 'DEEPSEEK_API_KEY',
}

function generateFernetKey(): string {
  // Fernet key = base64url-encoded 32 random bytes
  return crypto.randomBytes(32).toString('base64url')
}

function generateSecret(bytes = 32): string {
  return crypto.randomBytes(bytes).toString('hex')
}

async function testProviderKey(provider: (typeof INIT_PROVIDERS)[0], key: string): Promise<{ ok: boolean; models?: string[] }> {
  const t0 = Date.now()
  if (provider.type === 'anthropic') {
    // Anthropic uses different auth header
    try {
      const res = await fetch('https://api.anthropic.com/v1/models', {
        headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01' },
        signal: AbortSignal.timeout(8000),
      })
      if (!res.ok) return { ok: false }
      const data = await res.json() as { data?: Array<{ id: string }> }
      return { ok: true, models: data.data?.map(m => m.id) ?? [] }
    } catch {
      return { ok: false }
    }
  }
  // OpenAI-compatible
  try {
    const res = await fetch(`${provider.baseUrl}/models`, {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(8000),
    })
    if (!res.ok) return { ok: false }
    const data = await res.json() as { data?: Array<{ id: string }> }
    return { ok: true, models: data.data?.slice(0, 5).map(m => m.id) ?? [] }
  } catch {
    return { ok: false }
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

export interface InitOptions {
  supabaseUrl?: string
  supabaseAnonKey?: string
  supabaseServiceKey?: string
  anthropicKey?: string
  openrouterKey?: string
  serperKey?: string
  resendKey?: string
  yes?: boolean
  noMigrations?: boolean
}

export async function runInit(opts: InitOptions = {}): Promise<void> {
  const nonInteractive = !!(opts.supabaseUrl || opts.yes)

  printLogo(VERSION)

  if (nonInteractive) {
    info('Running in non-interactive mode')
  }

  p.intro(chalk.hex('#f5f0e8').bold('  ZeroHuman Agency — Setup'))

  // ── Step 1: Environment ────────────────────────────────────────────────────
  printSection('Step 1 / 8  Environment')

  const s1 = p.spinner()
  s1.start('Checking environment')

  const envChecks: CheckResult[] = []

  const nodeVer = process.version
  envChecks.push({ label: 'Node.js', status: 'ok', detail: nodeVer })

  let pythonVer = null
  try { pythonVer = execSync('python3 --version 2>&1').toString().trim() } catch {}
  envChecks.push({ label: 'Python', status: pythonVer ? 'ok' : 'warn', detail: pythonVer ?? 'not found' })

  let uvVer = null
  try { uvVer = execSync('uv --version 2>&1').toString().trim() } catch {}
  envChecks.push({ label: 'uv', status: uvVer ? 'ok' : 'warn', detail: uvVer ?? 'not found (install: pip install uv)' })

  let dockerVer = null
  try { dockerVer = execSync('docker --version 2>&1').toString().trim() } catch {}
  envChecks.push({ label: 'Docker', status: dockerVer ? 'ok' : 'skip', detail: dockerVer ?? 'not found (optional)' })

  s1.stop('Environment checked')
  console.log(formatTable(envChecks))
  console.log()

  // ── Step 2: Supabase ───────────────────────────────────────────────────────
  printSection('Step 2 / 8  Supabase')

  let supabaseUrl = opts.supabaseUrl ?? ''
  let supabaseAnonKey = opts.supabaseAnonKey ?? ''
  let supabaseServiceKey = opts.supabaseServiceKey ?? ''

  // Check for existing values
  const existing = readEnv()
  if (!supabaseUrl) supabaseUrl = existing.NEXT_PUBLIC_SUPABASE_URL ?? ''
  if (!supabaseAnonKey) supabaseAnonKey = existing.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ''
  if (!supabaseServiceKey) supabaseServiceKey = existing.SUPABASE_SERVICE_ROLE_KEY ?? ''

  if (supabaseUrl && supabaseAnonKey) {
    info(`Using existing Supabase config: ${supabaseUrl}`)
  } else if (!nonInteractive) {
    info('You need a Supabase project. Create one free at https://supabase.com')
    console.log()

    supabaseUrl = (await p.text({
      message: 'Supabase Project URL',
      placeholder: 'https://xxx.supabase.co',
      validate: v => (!v.startsWith('https://') ? 'Must start with https://' : undefined),
    })) as string
    if (p.isCancel(supabaseUrl)) { p.cancel('Setup cancelled'); process.exit(0) }

    supabaseAnonKey = (await p.text({
      message: 'Anon / Public Key',
      placeholder: 'eyJ...',
      validate: v => (!v.startsWith('eyJ') ? 'Must be a JWT starting with eyJ' : undefined),
    })) as string
    if (p.isCancel(supabaseAnonKey)) { p.cancel('Setup cancelled'); process.exit(0) }

    supabaseServiceKey = (await p.text({
      message: 'Service Role Key (optional but recommended)',
      placeholder: 'eyJ...',
    })) as string
    if (p.isCancel(supabaseServiceKey)) supabaseServiceKey = ''
  }

  // Test connection
  const s2 = p.spinner()
  s2.start('Testing Supabase connection')
  const supabaseCheck = await checkSupabase(supabaseUrl, supabaseAnonKey)
  s2.stop(supabaseCheck.status === 'ok' ? 'Supabase connected' : 'Supabase check failed')
  if (supabaseCheck.status !== 'ok') {
    fail(`Could not connect: ${supabaseCheck.detail}`)
    fail('Check your URL and keys, then run zh init again')
    process.exit(1)
  }
  ok(`Connected to ${supabaseUrl} (${supabaseCheck.latency_ms}ms)`)
  console.log()

  // ── Step 3: LLM Provider ──────────────────────────────────────────────────
  printSection('Step 3 / 8  LLM Provider')
  info('At least one LLM provider is required.')
  console.log()

  const configuredProviders: Record<string, string> = {}

  // Pre-fill from opts or existing env
  if (opts.anthropicKey) configuredProviders['ANTHROPIC_API_KEY'] = opts.anthropicKey
  if (opts.openrouterKey) configuredProviders['OPENROUTER_API_KEY'] = opts.openrouterKey
  for (const prov of INIT_PROVIDERS) {
    const envKey = ENV_KEY_FOR_PROVIDER[prov.id]
    if (envKey && existing[envKey]) configuredProviders[envKey] = existing[envKey]
  }

  if (Object.keys(configuredProviders).length === 0 && !nonInteractive) {
    let done = false
    while (!done) {
      const selected = await p.select({
        message: 'Select a provider to configure',
        options: [
          ...INIT_PROVIDERS.map(prov => ({
            value: prov.id,
            label: prov.label,
            hint: configuredProviders[ENV_KEY_FOR_PROVIDER[prov.id] ?? ''] ? '✓ configured' : '',
          })),
          { value: 'done', label: 'Done — continue with configured providers' },
        ],
      })
      if (p.isCancel(selected) || selected === 'done') {
        done = true
        continue
      }

      const prov = INIT_PROVIDERS.find(p => p.id === selected)!
      const apiKey = await p.text({
        message: `${prov.label} API key`,
        placeholder: `${prov.prefix}...`,
      })
      if (p.isCancel(apiKey)) continue

      const s3 = p.spinner()
      s3.start(`Testing ${prov.label} key`)
      const result = await testProviderKey(prov, apiKey as string)
      s3.stop(result.ok ? `${prov.label} validated` : `${prov.label} failed`)

      if (result.ok) {
        ok(`${prov.label} — ${result.models?.slice(0,3).join(', ')}`)
        configuredProviders[ENV_KEY_FOR_PROVIDER[prov.id]] = apiKey as string

        const addMore = await p.confirm({ message: 'Add another provider?' })
        if (!addMore || p.isCancel(addMore)) done = true
      } else {
        fail('Key validation failed — check the key and try again')
      }
    }
  }

  if (Object.keys(configuredProviders).length === 0) {
    fail('No LLM provider configured. At least one is required.')
    process.exit(1)
  }
  console.log()

  // ── Step 4: Encryption Keys ───────────────────────────────────────────────
  printSection('Step 4 / 8  Encryption Keys')

  const brandSecretsKey = existing.BRAND_SECRETS_ENCRYPTION_KEY || generateFernetKey()
  const schedulerSecret = existing.SCHEDULER_SECRET || generateSecret(32)

  ok(`BRAND_SECRETS_ENCRYPTION_KEY  ${existing.BRAND_SECRETS_ENCRYPTION_KEY ? '(existing)' : '(generated)'}`)
  ok(`SCHEDULER_SECRET              ${existing.SCHEDULER_SECRET ? '(existing)' : '(generated)'}`)
  console.log()

  // ── Step 5: Optional Services ─────────────────────────────────────────────
  printSection('Step 5 / 8  Optional Services')
  info('All optional — press Enter to skip each one.')
  console.log()

  const optional: Record<string, string> = {}

  if (!nonInteractive) {
    const serperKey = (await p.text({
      message: 'Serper API key (web search — get at serper.dev)',
      placeholder: 'skip',
      initialValue: opts.serperKey ?? existing.SERPER_API_KEY ?? '',
    })) as string
    if (!p.isCancel(serperKey) && serperKey && serperKey !== 'skip') optional['SERPER_API_KEY'] = serperKey

    const tavilyKey = (await p.text({
      message: 'Tavily API key (research — 1000 searches/month free)',
      placeholder: 'skip',
      initialValue: existing.TAVILY_API_KEY ?? '',
    })) as string
    if (!p.isCancel(tavilyKey) && tavilyKey && tavilyKey !== 'skip') optional['TAVILY_API_KEY'] = tavilyKey

    const youtubeKey = (await p.text({
      message: 'YouTube Data API key (trend research)',
      placeholder: 'skip',
      initialValue: existing.YOUTUBE_API_KEY ?? '',
    })) as string
    if (!p.isCancel(youtubeKey) && youtubeKey && youtubeKey !== 'skip') optional['YOUTUBE_API_KEY'] = youtubeKey

    const resendKey = (await p.text({
      message: 'Resend API key (email delivery — get at resend.com)',
      placeholder: 'skip',
      initialValue: opts.resendKey ?? existing.RESEND_API_KEY ?? '',
    })) as string
    if (!p.isCancel(resendKey) && resendKey && resendKey !== 'skip') optional['RESEND_API_KEY'] = resendKey
  } else {
    if (opts.serperKey) optional['SERPER_API_KEY'] = opts.serperKey
    if (opts.resendKey) optional['RESEND_API_KEY'] = opts.resendKey
  }

  // ── Step 6: Preview + Write ───────────────────────────────────────────────
  printSection('Step 6 / 8  Write Configuration')

  const toWrite: Record<string, string> = {
    NEXT_PUBLIC_SUPABASE_URL: supabaseUrl,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: supabaseAnonKey,
    ...(supabaseServiceKey ? { SUPABASE_SERVICE_ROLE_KEY: supabaseServiceKey } : {}),
    ...configuredProviders,
    BRAND_SECRETS_ENCRYPTION_KEY: brandSecretsKey,
    SCHEDULER_SECRET: schedulerSecret,
    ...optional,
  }

  console.log()
  for (const [k, v] of Object.entries(toWrite)) {
    const display = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD'].some(s => k.toUpperCase().includes(s))
      ? maskSecret(v)
      : v
    console.log(`  ${chalk.hex('#555')(k.padEnd(38))} ${chalk.hex('#f5f0e8')(display)}`)
  }
  console.log()

  let confirm = true
  if (!nonInteractive) {
    confirm = (await p.confirm({ message: 'Write these values to .env.local?' })) as boolean
    if (p.isCancel(confirm) || !confirm) { p.cancel('Setup cancelled'); process.exit(0) }
  }

  writeEnv(toWrite)
  ok('.env.local written')
  console.log()

  // ── Step 7: Database ──────────────────────────────────────────────────────
  printSection('Step 7 / 8  Database')

  if (!opts.noMigrations) {
    const runMigrations = !nonInteractive
      ? ((await p.confirm({ message: 'Apply Supabase migrations now?' })) as boolean)
      : true

    if (runMigrations && !p.isCancel(runMigrations)) {
      // Try supabase CLI if available
      try {
        const sbVer = execSync('supabase --version 2>&1').toString().trim()
        info(`Using Supabase CLI (${sbVer})`)
        const result = spawnSync('supabase', ['db', 'push', '--linked'], { stdio: 'inherit' })
        if (result.status === 0) {
          ok('Migrations applied')
        } else {
          warn('Migration command failed — run `supabase db push` manually')
        }
      } catch {
        warn('Supabase CLI not found — install it to run migrations: https://supabase.com/docs/guides/cli')
        warn('Or run migrations manually: supabase db push')
      }
    } else {
      info('Skipping migrations — run `zh migrate` when ready')
    }
  } else {
    info('Migrations skipped (--no-migrations)')
  }
  console.log()

  // ── Step 8: Health Check ──────────────────────────────────────────────────
  printSection('Step 8 / 8  Health Check')

  const backendUrl = existing.PYTHON_BACKEND_URL ?? 'http://localhost:8082'
  const healthChecks = await Promise.all([
    checkSupabase(supabaseUrl, supabaseAnonKey),
    checkBackend(backendUrl),
  ])

  console.log(formatTable(healthChecks))
  console.log()

  const allOk = healthChecks.every(c => c.status === 'ok')
  if (!allOk) {
    warn('Some checks failed — start services with: npm run dev')
  }

  p.outro(chalk.hex('#f5f0e8').bold('  Setup complete!') + '\n\n' +
    chalk.hex('#555')('  Run: ') + chalk.hex('#f5f0e8')('npm run dev') +
    chalk.hex('#555')('  to start ZeroHuman Agency'))
}
