'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, Video, Play, Download, ChevronDown, ChevronUp } from 'lucide-react'

interface Template {
  id: string
  name: string
  slug: string
  description?: string
  props_schema: Record<string, any>
}

interface VideoJob {
  id: string
  title: string
  status: 'pending' | 'rendering' | 'completed' | 'failed'
  output_url?: string
  duration_secs?: number
  error?: string
  created_at: string
}

const STATUS_BADGE: Record<string, string> = {
  pending: 'secondary',
  rendering: 'default',
  completed: 'outline',
  failed: 'destructive',
}

export default function VideosPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [videos, setVideos] = useState<VideoJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [props, setProps] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    const [tRes, vRes] = await Promise.all([
      fetch('/api/video/templates'),
      fetch('/api/video'),
    ])
    if (tRes.ok) {
      const t: Template[] = await tRes.json()
      setTemplates(t)
      if (!selectedTemplate && t.length > 0) setSelectedTemplate(t[0])
    }
    if (vRes.ok) setVideos(await vRes.json())
    setLoading(false)
  }, [selectedTemplate])

  useEffect(() => {
    loadData()
    const iv = setInterval(loadData, 10_000)
    return () => clearInterval(iv)
  }, [loadData])

  // Initialise prop fields when template changes
  useEffect(() => {
    if (!selectedTemplate) return
    const schema = selectedTemplate.props_schema?.properties ?? {}
    const defaults: Record<string, string> = {}
    for (const [k, v] of Object.entries(schema as Record<string, any>)) {
      defaults[k] = String(v.default ?? '')
    }
    // Pre-fill week_start with current Monday
    if ('week_start' in defaults) {
      const now = new Date()
      const day = now.getDay()
      const diff = (day === 0 ? -6 : 1) - day
      const monday = new Date(now)
      monday.setDate(now.getDate() + diff)
      defaults['week_start'] = monday.toISOString().slice(0, 10)
    }
    setProps(defaults)
  }, [selectedTemplate])

  async function submit() {
    if (!selectedTemplate) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_slug: selectedTemplate.slug,
          render_props: props,
        }),
      })
      if (res.ok) await loadData()
    } finally {
      setSubmitting(false)
    }
  }

  const schema = selectedTemplate?.props_schema?.properties ?? {}
  const required: string[] = selectedTemplate?.props_schema?.required ?? []

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Videos</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Render animated video recaps via HyperFrames. Output stored in Supabase Storage.
        </p>
      </div>

      {/* Template selector + render form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Video className="h-4 w-4" /> Render a Video
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Template picker */}
          <div>
            <Label>Template</Label>
            <div className="flex gap-2 mt-1 flex-wrap">
              {templates.map(t => (
                <button
                  key={t.id}
                  onClick={() => setSelectedTemplate(t)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                    selectedTemplate?.id === t.id
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border hover:bg-muted'
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>
            {selectedTemplate?.description && (
              <p className="text-xs text-muted-foreground mt-1">{selectedTemplate.description}</p>
            )}
          </div>

          {/* Dynamic prop fields */}
          {Object.entries(schema as Record<string, any>).map(([key, field]) => (
            <div key={key}>
              <Label>
                {field.label ?? key}
                {required.includes(key) && <span className="text-destructive ml-1">*</span>}
              </Label>
              <Input
                className="mt-1"
                placeholder={field.description ?? String(field.default ?? '')}
                value={props[key] ?? ''}
                onChange={e => setProps(p => ({ ...p, [key]: e.target.value }))}
              />
            </div>
          ))}

          <Button
            onClick={submit}
            disabled={submitting || !selectedTemplate}
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            Start Render
          </Button>
        </CardContent>
      </Card>

      {/* Video history */}
      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
          </div>
        ) : videos.length === 0 ? (
          <p className="text-sm text-muted-foreground">No videos yet.</p>
        ) : (
          videos.map(v => (
            <Card key={v.id} className="overflow-hidden">
              <div className="flex items-center gap-3 p-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{v.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {new Date(v.created_at).toLocaleString()}
                    {v.duration_secs && ` · ${v.duration_secs}s`}
                  </p>
                </div>
                <Badge variant={(STATUS_BADGE[v.status] as any) ?? 'secondary'}>
                  {v.status}
                </Badge>
                {v.status === 'rendering' && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {v.status === 'completed' && v.output_url && (
                  <div className="flex gap-1">
                    <a
                      href={v.output_url}
                      target="_blank"
                      rel="noopener"
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-muted transition-colors"
                    >
                      <Play className="h-4 w-4" />
                    </a>
                    <a
                      href={v.output_url}
                      download
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-muted transition-colors"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  </div>
                )}
                {v.status === 'failed' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setExpanded(expanded === v.id ? null : v.id)}
                  >
                    {expanded === v.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                )}
              </div>
              {expanded === v.id && v.error && (
                <div className="border-t bg-destructive/5 p-3">
                  <p className="text-xs text-destructive font-mono">{v.error}</p>
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
