import { requireAuth } from '@/lib/supabase/auth-helpers'
import { jsonResponse } from '@/lib/api-helpers'
import { readdir, readFile } from 'fs/promises'
import { join } from 'path'

const TEMPLATES_DIR = join(process.cwd(), 'data', 'brand-templates')

export async function GET() {
  const { auth, response } = await requireAuth()
  if (!auth) return response

  try {
    const files = await readdir(TEMPLATES_DIR)
    const templates = await Promise.all(
      files
        .filter(f => f.endsWith('.json'))
        .map(async f => {
          const content = await readFile(join(TEMPLATES_DIR, f), 'utf-8')
          return JSON.parse(content)
        })
    )
    // Sort: generic last
    templates.sort((a, b) => (a.id === 'generic' ? 1 : b.id === 'generic' ? -1 : 0))
    return jsonResponse(templates)
  } catch {
    return jsonResponse([])
  }
}
