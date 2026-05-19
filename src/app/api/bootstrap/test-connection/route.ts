import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

// Only active when Supabase is NOT yet configured
function isSetupMode() {
  return !process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
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

  const { supabase_url, supabase_anon_key } = body
  if (!supabase_url || !supabase_anon_key) {
    return NextResponse.json({ error: 'supabase_url and supabase_anon_key are required' }, { status: 400 })
  }

  try {
    const client = createClient(supabase_url, supabase_anon_key)
    // Lightweight probe: fetch the health endpoint
    const { error } = await client.from('brands').select('id').limit(1)
    if (error && error.code !== 'PGRST116') {
      // PGRST116 = table doesn't exist yet (migrations not run) — still means DB is reachable
      throw new Error(error.message)
    }
    return NextResponse.json({ success: true, message: 'Connection successful' })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ success: false, error: msg }, { status: 200 })
  }
}
