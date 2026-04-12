import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import type { Database } from '@/lib/types/database.types'

type ItemStatus = Database['public']['Enums']['item_status']
const VALID_STATUSES: ItemStatus[] = ['new', 'scored', 'approved', 'rejected', 'archived']

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await request.json()
  const status = body.status as ItemStatus

  if (!VALID_STATUSES.includes(status)) {
    return errorResponse('Invalid status', 400)
  }

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('research_items')
    .update({ status })
    .eq('id', id)
    .select()
    .single()

  if (error) return errorResponse(error.message, 500)
  if (!data) return errorResponse('Item not found', 404)

  return jsonResponse(data)
}
