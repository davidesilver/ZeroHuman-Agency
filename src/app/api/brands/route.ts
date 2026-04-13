import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data, error } = await supabase
      .from('brands')
      .select('id, name, slug')
      .order('name')

    if (error) return errorResponse(error.message, 500)

    return jsonResponse(data || [])
  } catch (err) {
    return errorResponse('Failed to fetch brands', 500)
  }
}
