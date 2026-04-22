/**
 * Server-side auth helpers for Next.js API routes.
 *
 * P1 update (migration 017): multi-brand N:M support.
 *
 * requireAuth() now:
 *   1. Verifies the Supabase session.
 *   2. Loads ALL brands the user is a member of from brand_members.
 *   3. Reads the `active_brand_id` cookie to determine the working brand.
 *   4. Falls back to the first (oldest) membership if the cookie is absent or
 *      no longer valid (e.g. user was removed from that brand).
 *
 * The returned AuthContext carries:
 *   - userId          — Supabase auth.users.id
 *   - brandId         — the ACTIVE brand for this request (same as activeBrandId)
 *   - activeBrandId   — active brand (preferred field name going forward)
 *   - memberBrandIds  — all brands the user is a member of
 *
 * COOKIE NAME: "active_brand_id"
 *   Set by BrandProvider (client side) when the user switches brands.
 *   Read here (server side) on every API route call.
 *   This is a plain session cookie (HttpOnly not required — it's not a secret).
 */

import { createClient } from '@/lib/supabase/server'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export const ACTIVE_BRAND_COOKIE = 'active_brand_id'

export interface AuthContext {
  userId: string
  /** Active brand for this request — use this everywhere. */
  brandId: string
  /** Alias of brandId — preferred name post-P1. */
  activeBrandId: string
  /** All brands this user is a member of. */
  memberBrandIds: string[]
}

/**
 * Resolve the authenticated user and their active brand from the current session.
 *
 * Returns `null` + an appropriate error response if:
 *  - The session is missing/invalid → 401
 *  - The user has no brand memberships at all → 404
 *
 * Usage:
 * ```ts
 * const { auth, response } = await requireAuth()
 * if (!auth) return response
 * // auth.brandId is the active brand
 * // auth.memberBrandIds is the full membership set
 * ```
 */
export async function requireAuth(): Promise<
  { auth: AuthContext; response: null } | { auth: null; response: NextResponse }
> {
  const supabase = await createClient()

  // 1. Verify the session
  const {
    data: { user },
    error: sessionError,
  } = await supabase.auth.getUser()

  if (sessionError || !user) {
    return {
      auth: null,
      response: NextResponse.json(
        { success: false, error: { message: 'Unauthorized' } },
        { status: 401 }
      ),
    }
  }

  // 2. Load ALL brand memberships for this user (N:M via brand_members).
  //    Falls back gracefully if brand_members doesn't exist yet (pre-017
  //    databases) by catching the error and trying the legacy users.brand_id.
  let memberBrandIds: string[] = []

  const { data: memberships, error: memberError } = await supabase
    .from('brand_members')
    .select('brand_id')
    .eq('user_id', user.id)
    .order('created_at', { ascending: true })

  if (!memberError && memberships && memberships.length > 0) {
    memberBrandIds = memberships.map((m) => m.brand_id)
  } else {
    // Pre-017 fallback: read from users.brand_id (1:1 old model)
    const { data: userRecord } = await supabase
      .from('users')
      .select('brand_id')
      .eq('id', user.id)
      .single()

    if (userRecord?.brand_id) {
      memberBrandIds = [userRecord.brand_id]
    }
  }

  if (memberBrandIds.length === 0) {
    return {
      auth: null,
      response: NextResponse.json(
        { success: false, error: { message: 'No brand membership found for user' } },
        { status: 404 }
      ),
    }
  }

  // 3. Resolve active brand from cookie, validating it's still in membership.
  const cookieStore = await cookies()
  const cookieBrandId = cookieStore.get(ACTIVE_BRAND_COOKIE)?.value ?? null
  const activeBrandId = cookieBrandId && memberBrandIds.includes(cookieBrandId)
    ? cookieBrandId
    : memberBrandIds[0]  // fallback: oldest membership

  return {
    auth: {
      userId: user.id,
      brandId: activeBrandId,
      activeBrandId,
      memberBrandIds,
    },
    response: null,
  }
}
