'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Loader2, Globe, Plus, Trash2 } from 'lucide-react'

interface Snapshot {
  id: string
  url: string
  title?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  captured_at?: string
  created_at: string
  error?: string
}

export default function CompetitorWatchPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [urls, setUrls] = useState<string[]>([''])
  const [submitting, setSubmitting] = useState(false)

  const loadSnapshots = useCallback(async () => {
    const res = await fetch('/api/research/competitor/snapshots?limit=50')
    if (res.ok) setSnapshots(await res.json())
    setLoading(false)
  }, [])

  useEffect(() => {
    loadSnapshots()
    const interval = setInterval(loadSnapshots, 15_000)
    return () => clearInterval(interval)
  }, [loadSnapshots])

  async function submit() {
    const validUrls = urls.filter(u => u.trim())
    if (!validUrls.length) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/research/competitor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: validUrls }),
      })
      if (res.ok) {
        setUrls([''])
        await loadSnapshots()
      }
    } finally {
      setSubmitting(false)
    }
  }

  const STATUS_BADGE: Record<string, string> = {
    pending: 'secondary',
    running: 'default',
    completed: 'outline',
    failed: 'destructive',
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Competitor Watch</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Periodic competitor page snapshots using Scrapling (stealth mode, anti-Cloudflare).
        </p>
      </div>

      {/* Add URLs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4" /> Monitor URLs
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {urls.map((url, i) => (
            <div key={i} className="flex gap-2">
              <Input
                placeholder="https://competitor.com/blog"
                value={url}
                onChange={e => {
                  const next = [...urls]
                  next[i] = e.target.value
                  setUrls(next)
                }}
              />
              {urls.length > 1 && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setUrls(urls.filter((_, j) => j !== i))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setUrls([...urls, ''])}>
              <Plus className="h-4 w-4 mr-1" /> Add URL
            </Button>
            <Button size="sm" onClick={submit} disabled={submitting || !urls.some(u => u.trim())}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
              Capture Snapshots
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Snapshots history */}
      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
          </div>
        ) : snapshots.length === 0 ? (
          <p className="text-sm text-muted-foreground">No snapshots yet.</p>
        ) : (
          snapshots.map(s => (
            <Card key={s.id}>
              <div className="flex items-center gap-3 p-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{s.title ?? s.url}</p>
                  <p className="text-xs text-muted-foreground truncate">{s.url}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {s.captured_at
                      ? `Captured ${new Date(s.captured_at).toLocaleString()}`
                      : new Date(s.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={(STATUS_BADGE[s.status] as any) ?? 'secondary'}>
                  {s.status}
                </Badge>
                {s.status === 'running' && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
