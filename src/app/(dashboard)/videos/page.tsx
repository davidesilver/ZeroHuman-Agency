'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FeatureGate } from '@/components/ui/feature-gate'
import { ErrorCard } from '@/components/ui/error-card'
import { EmptyState } from '@/components/ui/empty-state'
import { usePolling } from '@/hooks/use-polling'
import { getStatusVariant } from '@/lib/status-colors'
import { useBrand } from '@/lib/brand-context'
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

function VideosContent() {
  const { activeBrand } = useBrand()
  const [templates, setTemplates] = useState<Template[]>([])
  const [videos, setVideos] = useState<VideoJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [props, setProps] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      const [tRes, vRes] = await Promise.all([
        fetch('/api/video/templates'),
        fetch('/api/video'),
      ])
      if (!tRes.ok || !vRes.ok) {
        setError(`Failed to load video data (templates: ${tRes.status}, videos: ${vRes.status})`)
        setLoading(false)
        return
      }
      const t: Template[] = await tRes.json()
      setTemplates(t)
      if (!selectedTemplate && t.length > 0) setSelectedTemplate(t[0])
      setVideos(await vRes.json())
      setError(null)
    } catch {
      setError('Unable to reach video service')
    } finally {
      setLoading(false)
    }
  }, [selectedTemplate])

  usePolling(loadData, 10_000)

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
    setSubmitError(null)
    try {
      const res = await fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_slug: selectedTemplate.slug,
          render_props: props,
        }),
      })
      if (!res.ok) {
        setSubmitError(`Render failed (${res.status})`)
        return
      }
      await loadData()
    } catch {
      setSubmitError('Network error — unable to start render')
    } finally {
      setSubmitting(false)
    }
  }

  if (!activeBrand) {
    return (
      <div className="p-6 max-w-3xl">
        <EmptyState icon={Video} message="Select a brand to render videos." />
      </div>
    )
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

          {submitError && (
            <p className="text-xs text-destructive">{submitError}</p>
          )}
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
        {error ? (
          <ErrorCard message={error} onRetry={loadData} />
        ) : loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
          </div>
        ) : videos.length === 0 ? (
          <EmptyState icon={Video} message="No videos yet." />
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
                <Badge variant={(getStatusVariant(v.status)) as any}>
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

export default function VideosPage() {
  const { activeBrand } = useBrand()
  return (
    <FeatureGate flag="video_enabled" brandId={activeBrand?.id}>
      <VideosContent />
    </FeatureGate>
  )
}
