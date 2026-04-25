'use client'

import { useState, useEffect, useCallback } from 'react'
import { Send, Loader2, AlertCircle, Check } from 'lucide-react'

interface Integration {
  platform: string
  postiz_integration_id: string
  postiz_channel_name: string | null
  is_active: boolean
}

interface PublishButtonProps {
  draftId: string
  onPublished?: () => void
}

export function PublishButton({ draftId, onPublished }: PublishButtonProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    fetch('/api/social/integrations/mine')
      .then((r) => r.json())
      .then((json) => {
        if (json.success) {
          const rows = (json.data || []).filter((i: Integration) => i.is_active && i.postiz_integration_id)
          setIntegrations(rows)
          // Auto-select all by default
          setSelected(new Set(rows.map((r: Integration) => r.platform)))
        }
        setFetching(false)
      })
      .catch(() => setFetching(false))
  }, [])

  const togglePlatform = useCallback((platform: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(platform)) next.delete(platform)
      else next.add(platform)
      return next
    })
  }, [])

  async function handlePublish() {
    if (selected.size === 0) return
    setLoading(true)
    setError(null)
    setSuccess(false)
    try {
      const r = await fetch('/api/social/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          draft_id: draftId,
          platforms: Array.from(selected),
        }),
      })
      const json = await r.json()
      if (!r.ok || !json.success) {
        throw new Error(json.error?.message || 'Publish failed')
      }
      setSuccess(true)
      onPublished?.()
      setTimeout(() => setSuccess(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  if (fetching) {
    return (
      <div className="text-xs text-muted-foreground inline-flex items-center gap-1">
        <Loader2 size={12} className="animate-spin" />
        Loading platforms…
      </div>
    )
  }

  if (integrations.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        No social platforms connected.{' '}
        <a href="/settings/social-connections" className="underline">Connect in Settings</a>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {integrations.map((intg) => (
          <button
            key={intg.platform}
            onClick={() => togglePlatform(intg.platform)}
            className={`px-2 py-0.5 rounded text-[10px] border transition-colors ${
              selected.has(intg.platform)
                ? 'bg-black text-white border-black'
                : 'bg-white text-muted-foreground border-gray-200 hover:border-gray-400'
            }`}
            title={intg.postiz_channel_name || intg.platform}
          >
            {intg.platform}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handlePublish}
          disabled={loading || selected.size === 0}
          className="px-3 py-1.5 rounded bg-brand-primary text-white text-xs inline-flex items-center gap-1.5 disabled:opacity-50"
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> :
           success ? <Check size={12} /> : <Send size={12} />}
          {loading ? 'Publishing…' : success ? 'Published!' : 'Publish now'}
        </button>
        <span className="text-[10px] text-muted-foreground">
          {selected.size} platform{selected.size !== 1 ? 's' : ''} selected
        </span>
      </div>

      {error && (
        <div className="flex items-center gap-1 text-[10px] text-red-600">
          <AlertCircle size={10} />
          {error}
        </div>
      )}
    </div>
  )
}
