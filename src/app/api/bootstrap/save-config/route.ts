import { NextRequest, NextResponse } from 'next/server'
import { writeFileSync, renameSync, existsSync, readFileSync } from 'fs'
import { resolve } from 'path'

// Only active when Supabase is NOT yet configured
function isSetupMode() {
  return !process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
}

function getEnvPath(): string {
  // .env.local lives at the project root (one level above src/)
  return resolve(process.cwd(), '.env.local')
}

function parseEnvFile(content: string): Record<string, string> {
  const result: Record<string, string> = {}
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const idx = trimmed.indexOf('=')
    if (idx === -1) continue
    const key = trimmed.slice(0, idx).trim()
    const val = trimmed.slice(idx + 1).trim()
    result[key] = val
  }
  return result
}

function serializeEnvFile(entries: Record<string, string>): string {
  return Object.entries(entries)
    .map(([k, v]) => `${k}=${v}`)
    .join('\n') + '\n'
}

export async function POST(req: NextRequest) {
  if (!isSetupMode()) {
    return NextResponse.json({ error: 'Already configured' }, { status: 403 })
  }

  let body: { supabase_url?: string; supabase_anon_key?: string; supabase_service_key?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const { supabase_url, supabase_anon_key, supabase_service_key } = body
  if (!supabase_url || !supabase_anon_key) {
    return NextResponse.json({ error: 'supabase_url and supabase_anon_key are required' }, { status: 400 })
  }

  try {
    const envPath = getEnvPath()
    // Read existing .env.local if present, merge new values
    let existing: Record<string, string> = {}
    if (existsSync(envPath)) {
      existing = parseEnvFile(readFileSync(envPath, 'utf-8'))
    }

    existing['NEXT_PUBLIC_SUPABASE_URL'] = supabase_url
    existing['NEXT_PUBLIC_SUPABASE_ANON_KEY'] = supabase_anon_key
    if (supabase_service_key) {
      existing['SUPABASE_SERVICE_ROLE_KEY'] = supabase_service_key
    }

    // Atomic write via temp file
    const tmpPath = envPath + '.tmp'
    writeFileSync(tmpPath, serializeEnvFile(existing), 'utf-8')
    renameSync(tmpPath, envPath)

    return NextResponse.json({
      success: true,
      message: 'Configuration saved. Restart the server to apply changes.',
      restart_required: true,
    })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ success: false, error: msg }, { status: 500 })
  }
}
