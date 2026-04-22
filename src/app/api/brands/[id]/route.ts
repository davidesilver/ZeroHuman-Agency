/**
 * Brand update/delete endpoints.
 *
 * Scope (P0.3+): `name`, `topics`, and `research_sources` are editable.
 * `tone_of_voice` and `scoring_weights` are intentionally frozen because they
 * will migrate to the memory_semantic layer in P3 — exposing them here would
 * create a parallel write path that we'd have to unwind.
 *
 * Authorization model is transitional:
 *  - Today: caller must be the single user tied to this brand via users.brand_id.
 *  - After P1: swap to `brand_members` membership check with role='owner'|'admin'.
 * The guard below is deliberately explicit so the P1 refactor is a targeted
 * find-and-replace, not a behavior change that sneaks in data leaks.
 */

import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import type { Json } from '@/lib/types/database.types'

interface RouteContext {
  params: Promise<{ id: string }>
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}

export async function PATCH(request: Request, context: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await context.params
  if (!isUuid(id)) return errorResponse('Invalid brand id', 400)

  // P1: check membership instead of active-brand equality
  if (!auth.memberBrandIds.includes(id)) return errorResponse('Forbidden', 403)

  let body: { name?: string; topics?: string[]; research_sources?: Json }
  try {
    body = await request.json()
  } catch {
    return errorResponse('Invalid JSON body', 400)
  }

  const patch: { name?: string; topics?: string[]; research_sources?: Json } = {}
  if (body.name !== undefined) {
    if (typeof body.name !== 'string') return errorResponse('name must be a string', 400)
    const trimmed = body.name.trim()
    if (!trimmed) return errorResponse('name cannot be empty', 400)
    patch.name = trimmed
  }
  if (body.topics !== undefined) {
    if (!Array.isArray(body.topics)) return errorResponse('topics must be an array', 400)
    patch.topics = body.topics
      .filter((t): t is string => typeof t === 'string')
      .map((t) => t.trim())
      .filter(Boolean)
  }
  if (body.research_sources !== undefined) {
    if (
      typeof body.research_sources !== 'object' ||
      Array.isArray(body.research_sources) ||
      body.research_sources === null
    ) {
      return errorResponse('research_sources must be an object', 400)
    }
    patch.research_sources = body.research_sources
  }
  if (Object.keys(patch).length === 0) {
    return errorResponse('No editable fields provided (allowed: name, topics, research_sources)', 400)
  }

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('brands')
    .update(patch)
    .eq('id', id)
    .select('id, name, slug, topics, tone_of_voice, scoring_weights, research_sources')
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Brand not found', 404)

  return jsonResponse(data)
}

export async function DELETE(_request: Request, context: RouteContext) {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  const { id } = await context.params
  if (!isUuid(id)) return errorResponse('Invalid brand id', 400)

  // P1: check membership — only brand members can delete
  if (!auth.memberBrandIds.includes(id)) return errorResponse('Forbidden', 403)

  const supabase = await createClient()

  // Safety rail: CASCADE chains on brand_id span ~17 tables (research_items,
  // content_drafts, newsletters, audit_trail, api_costs, ...). A single DELETE
  // call will nuke all of it — that's intentional per user flow ("remove a
  // brand") but we refuse when content is present so the user can confirm.
  const { count: draftCount } = await supabase
    .from('content_drafts')
    .select('id', { count: 'exact', head: true })
    .eq('brand_id', id)

  if ((draftCount ?? 0) > 0) {
    return errorResponse(
      `Brand has ${draftCount} content drafts. Archive or delete drafts before removing the brand.`,
      409,
    )
  }

  const { error } = await supabase.from('brands').delete().eq('id', id)
  if (error) return errorResponse(error.message, 500)

  return jsonResponse({ deleted: id })
}
