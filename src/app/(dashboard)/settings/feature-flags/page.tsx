'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ErrorCard } from '@/components/ui/error-card'
import { EmptyState } from '@/components/ui/empty-state'
import { useBrand } from '@/lib/brand-context'
import { Loader2, ToggleLeft, ToggleRight, Flag } from 'lucide-react'

/** Known flags with descriptions (mirrors Python feature_flags.py constants) */
const FLAG_REGISTRY: { key: string; label: string; description: string }[] = [
  {
    key: 'video_enabled',
    label: 'Video generation',
    description: 'HyperFrames rendering and video template management.',
  },
  {
    key: 'email_marketing_enabled',
    label: 'Email marketing (Brevo)',
    description: 'Brevo contacts, campaigns, and automations.',
  },
  {
    key: 'deep_research_enabled',
    label: 'Deep research',
    description: 'Async multi-source research via local-deep-research sidecar.',
  },
  {
    key: 'competitor_monitoring_enabled',
    label: 'Competitor monitoring',
    description: 'Stealth page snapshots via Scrapling.',
  },
]

export default function FeatureFlagsPage() {
  const { activeBrand } = useBrand()
  const brandId = activeBrand?.id
  const [flags, setFlags] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)

  const loadFlags = useCallback(async () => {
    if (!brandId) { setLoading(false); return }
    setError(null)
    try {
      const results: Record<string, boolean> = {}
      await Promise.all(
        FLAG_REGISTRY.map(async ({ key }) => {
          const res = await fetch(
            `/api/feature-flags?key=${encodeURIComponent(key)}&brand_id=${encodeURIComponent(brandId)}`
          )
          if (res.ok) {
            const data = await res.json()
            results[key] = !!data.value
          } else {
            results[key] = false
          }
        })
      )
      setFlags(results)
    } catch {
      setError('Unable to load feature flags')
    } finally {
      setLoading(false)
    }
  }, [brandId])

  useEffect(() => { loadFlags() }, [loadFlags])

  async function toggle(key: string) {
    if (!brandId) return
    const newValue = !flags[key]
    setSaving(key)
    try {
      const res = await fetch('/api/feature-flags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_id: brandId, key, value: newValue }),
      })
      if (res.ok) {
        setFlags(f => ({ ...f, [key]: newValue }))
      }
    } finally {
      setSaving(null)
    }
  }

  if (!activeBrand) {
    return (
      <div className="p-6 max-w-xl">
        <EmptyState icon={Flag} message="Select a brand to manage feature flags." />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 max-w-xl">
      <div>
        <h1 className="text-2xl font-semibold">Feature Flags</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Enable or disable capabilities for <strong>{activeBrand.name}</strong>.
          Changes take effect immediately.
        </p>
      </div>

      {error ? (
        <ErrorCard message={error} onRetry={loadFlags} />
      ) : loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading flags...
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Flag className="h-4 w-4" /> Capability Flags
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {FLAG_REGISTRY.map(({ key, label, description }) => (
              <div key={key} className="flex items-center gap-4 py-3 first:pt-0 last:pb-0">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggle(key)}
                  disabled={saving === key}
                  className="shrink-0"
                >
                  {saving === key ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : flags[key] ? (
                    <ToggleRight className="h-6 w-6 text-green-500" />
                  ) : (
                    <ToggleLeft className="h-6 w-6 text-muted-foreground" />
                  )}
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
