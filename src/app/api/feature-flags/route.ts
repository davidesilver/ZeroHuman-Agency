import { createClient } from '@/lib/supabase/server'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { NextResponse } from 'next/server'

/** GET /api/feature-flags?key=<key> — read a single flag for the active brand */
export async function GET(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const url = new URL(request.url)
  const key = url.searchParams.get('key')
  const brandId = url.searchParams.get('brand_id')

  if (!key) return NextResponse.json({ error: 'key is required' }, { status: 400 })

  const supabase = await createClient()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let query = (supabase as any).from('feature_flags').select('key, value, brand_id').eq('key', key)
  if (brandId) query = query.eq('brand_id', brandId)

  const { data } = await query.maybeSingle()
  return NextResponse.json(data ?? { key, value: null })
}

/** POST /api/feature-flags — upsert a flag for the active brand */
export async function POST(request: Request) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const body = await request.json().catch(() => null)
  if (!body?.key || body.value === undefined || !body.brand_id) {
    return NextResponse.json({ error: 'key, value, and brand_id are required' }, { status: 400 })
  }

  const supabase = await createClient()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { error } = await (supabase as any)
    .from('feature_flags')
    .upsert({ brand_id: body.brand_id, key: body.key, value: body.value }, { onConflict: 'brand_id,key' })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true })
}
