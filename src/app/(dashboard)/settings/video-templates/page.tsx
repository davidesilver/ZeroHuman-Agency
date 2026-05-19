'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, Video, Plus, ChevronDown, ChevronUp } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'

interface VideoTemplate {
  id: string
  name: string
  slug: string
  description?: string
  composition_path: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props_schema: Record<string, any>
  thumbnail_url?: string
  brand_id: string | null
}

export default function VideoTemplatesPage() {
  const { activeBrand } = useBrand()
  const [templates, setTemplates] = useState<VideoTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  // New template form state
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [compositionPath, setCompositionPath] = useState('')
  const [accentColor, setAccentColor] = useState('#6366f1')

  const load = useCallback(async () => {
    const res = await fetch('/api/video/templates')
    if (res.ok) setTemplates(await res.json())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  async function create() {
    if (!name.trim() || !slug.trim()) return
    setCreating(true)
    try {
      const res = await fetch('/api/video/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          slug: slug.trim().toLowerCase().replace(/\s+/g, '-'),
          description: description.trim() || undefined,
          composition_path: compositionPath.trim() || `compositions/${slug.trim()}`,
          props_schema: {
            type: 'object',
            properties: {
              brand_name: { type: 'string', description: 'Brand display name' },
              accent_color: { type: 'string', description: 'Hex accent color', default: accentColor },
              logo_url: { type: 'string', description: 'Logo URL' },
            },
          },
        }),
      })
      if (res.ok) {
        setShowForm(false)
        setName(''); setSlug(''); setDescription(''); setCompositionPath('')
        await load()
      }
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Video Templates</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Per-brand HyperFrames composition templates. System templates are shared across all brands.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowForm(v => !v)}>
          <Plus className="h-4 w-4 mr-1" /> New template
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Name</Label>
                <Input className="mt-1" value={name} onChange={e => setName(e.target.value)} placeholder="Monthly Report" />
              </div>
              <div>
                <Label>Slug</Label>
                <Input className="mt-1" value={slug} onChange={e => setSlug(e.target.value)} placeholder="monthly-report" />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Input className="mt-1" value={description} onChange={e => setDescription(e.target.value)} placeholder="Short description" />
            </div>
            <div>
              <Label>Composition path (relative to repo root)</Label>
              <Input className="mt-1" value={compositionPath} onChange={e => setCompositionPath(e.target.value)} placeholder="compositions/monthly-report" />
            </div>
            <div>
              <Label>Default accent color</Label>
              <div className="flex items-center gap-2 mt-1">
                <input type="color" value={accentColor} onChange={e => setAccentColor(e.target.value)} className="h-8 w-8 rounded border cursor-pointer" />
                <Input value={accentColor} onChange={e => setAccentColor(e.target.value)} className="font-mono" />
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={create} disabled={creating || !name.trim() || !slug.trim()}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Create
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Template list */}
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading templates...
        </div>
      ) : (
        <div className="space-y-2">
          {templates.map(t => (
            <Card key={t.id} className="overflow-hidden">
              <div className="flex items-center gap-3 p-3">
                <Video className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{t.name}</p>
                    <Badge variant={t.brand_id ? 'outline' : 'secondary'} className="text-[10px]">
                      {t.brand_id ? 'per-brand' : 'system'}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{t.composition_path}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
                  {expanded === t.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
              </div>
              {expanded === t.id && (
                <div className="border-t bg-muted/30 p-3">
                  {t.description && <p className="text-xs text-muted-foreground mb-2">{t.description}</p>}
                  <p className="text-xs font-medium mb-1">Props schema</p>
                  <pre className="text-xs font-mono bg-background rounded p-2 overflow-x-auto">
                    {JSON.stringify(t.props_schema, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
