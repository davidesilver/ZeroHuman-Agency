/**
 * Server-side auth helpers for Next.js API routes.
 *
 * Central place to retrieve the authenticated user and their brand_id from
 * the Supabase session. Using this in every route prevents relying solely on
 * RLS and avoids hardcoded brand UUIDs (C-07).
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export interface AuthContext {
  userId: string
  brandId: string
}

/**
 * Resolve the authenticated user and their brand_id from the current session.
 *
 * Returns `null` and sends a 401 response if the user is not authenticated,
 * or null + 404 if no brand record is found for the user.
 *
 * Usage:
 * ```ts
 * const { auth, response } = await requireAuth()
 * if (!auth) return response
 * // auth.brandId is now safe to use in queries
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

  // 2. Look up the brand_id tied to this user
  const { data: userRecord, error: userError } = await supabase
    .from('users')
    .select('brand_id')
    .eq('id', user.id)
    .single()

  if (userError || !userRecord?.brand_id) {
    return {
      auth: null,
      response: NextResponse.json(
        { success: false, error: { message: 'Brand not found for user' } },
        { status: 404 }
      ),
    }
  }

  return {
    auth: { userId: user.id, brandId: userRecord.brand_id },
    response: null,
  }
}
