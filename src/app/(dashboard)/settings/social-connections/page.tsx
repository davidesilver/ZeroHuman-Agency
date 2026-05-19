'use client'

import { useEffect, useState } from 'react'
import { Save, Trash2, Globe, Server, AlertCircle } from 'lucide-react'

const PLATFORMS = [
  { key: 'linkedin', label: 'LinkedIn', icon: '💼' },
  { key: 'twitter', label: 'X / Twitter', icon: '🐦' },
  { key: 'instagram', label: 'Instagram', icon: '📸' },
  { key: 'tiktok', label: 'TikTok', icon: '🎵' },
  { key: 'youtube', label: 'YouTube', icon: '▶️' },
  { key: 'threads', label: 'Threads', icon: '🧵' },
  { key: 'bluesky', label: 'Bluesky', icon: '🦋' },
  { key: 'pinterest', label: 'Pinterest', icon: '📌' },
  { key: 'reddit', label: 'Reddit', icon: '🔴' },
  { key: 'facebook', label: 'Facebook', icon: '👍' },
  { key: 'mastodon', label: 'Mastodon', icon: '🐘' },
  { key: 'discord', label: 'Discord', icon: '💬' },
  { key: 'slack', label: 'Slack', icon: '💼' },
] as const

interface Integration {
  id: string
  platform: string
  postiz_integration_id: string
  postiz_channel_name: string | null
  is_active: boolean
}

interface HealthStatus {
  status: string
  mode?: string
  error?: string
}

function PlatformCard({
  plat,
  existing,
  onSave,
  onRemove,
  saving,
}: {
  plat: (typeof PLATFORMS)[number]
  existing?: Integration
  onSave: (platform: string, id: string, name: string, active: boolean) => void
  onRemove: (platform: string) => void
  saving: string | null
}) {
  const [integrationId, setIntegrationId] = useState(existing?.postiz_integration_id || '')
  const [channelName, setChannelName] = useState(existing?.postiz_channel_name || '')
  const [isActive, setIsActive] = useState(existing?.is_active ?? true)

  useEffect(() => {
    setIntegrationId(existing?.postiz_integration_id || '')
    setChannelName(existing?.postiz_channel_name || '')
    setIsActive(existing?.is_active ?? true)
  }, [existing?.postiz_integration_id, existing?.postiz_channel_name, existing?.is_active])

  const isConnected = !!existing?.postiz_integration_id && existing.is_active

  return (
    <div className={`rounded-lg border p-4 space-y-3 ${
      isConnected ? 'border-[var(--status-success)]/30 bg-[var(--status-success)]/5' : 'border-hairline'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{plat.icon}</span>
          <span className="font-medium text-sm">{plat.label}</span>
        </div>
        {isConnected && (
          <span className="status-success-soft text-[11px] font-medium px-2 py-0.5 rounded-full">
            Connected
          </span>
        )}
      </div>

      <div className="space-y-2">
        <label className="block text-xs text-muted-foreground">
          Postiz Integration ID
          <input
            value={integrationId}
            onChange={(e) => setIntegrationId(e.target.value)}
            placeholder="Paste integration ID from Postiz"
            className="mt-1 block w-full border rounded px-2 py-1 text-xs font-mono"
          />
        </label>
        <label className="block text-xs text-muted-foreground">
          Channel name (optional)
          <input
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
            placeholder="e.g. MyBrand LinkedIn"
            className="mt-1 block w-full border rounded px-2 py-1 text-xs"
          />
        </label>
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          Active
        </label>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onSave(plat.key, integrationId, channelName, isActive)}
          disabled={saving === plat.key || !integrationId.trim()}
          className="flex-1 px-2 py-1.5 rounded bg-black text-white text-xs inline-flex items-center justify-center gap-1 disabled:opacity-50"
        >
          <Save size={12}/>
          {saving === plat.key ? 'Saving…' : existing ? 'Update' : 'Connect'}
        </button>
        {existing && (
          <button
            onClick={() => onRemove(plat.key)}
            className="px-2 py-1.5 rounded border border-hairline text-xs inline-flex items-center gap-1 text-[var(--status-error)] hover:bg-[var(--status-error)]/10"
          >
            <Trash2 size={12}/>
          </button>
        )}
      </div>
    </div>
  )
}

export default function SocialConnectionsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/social/health')
      .then((r) => r.json())
      .then((json) => setHealth(json.data || null))
      .catch(() => setHealth({ status: 'error', error: 'Backend unreachable' }))

    fetch('/api/social/integrations/mine')
      .then((r) => r.json())
      .then((json) => {
        if (json.success) setIntegrations(json.data || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  async function save(platform: string, integrationId: string, channelName: string, isActive: boolean) {
    setSaving(platform)
    const r = await fetch('/api/social/integrations/mine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform,
        postiz_integration_id: integrationId,
        postiz_channel_name: channelName || null,
        is_active: isActive,
      }),
    })
    const json = await r.json()
    if (json.success) {
      setIntegrations((prev) => {
        const idx = prev.findIndex((i) => i.platform === platform)
        if (idx >= 0) {
          const next = [...prev]
          next[idx] = json.data
          return next
        }
        return [...prev, json.data]
      })
    }
    setSaving(null)
  }

  async function remove(platform: string) {
    await fetch(`/api/social/integrations/mine/${platform}`, { method: 'DELETE' })
    setIntegrations((prev) => prev.filter((i) => i.platform !== platform))
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Social Connections</h1>
        <p className="text-sm text-ink-subtle">
          Connect social platforms via Postiz. OAuth is handled by Postiz — you only
          need to paste the integration IDs here.
        </p>
      </header>

      {/* Health Status */}
      {health && (
        <div className={`flex items-center gap-2 text-sm rounded-lg border px-3 py-2 ${
          health.status === 'ok' ? 'status-success-soft border-[var(--status-success)]/30' :
          health.status === 'disabled' ? 'bg-[var(--surface-1)] border-hairline text-ink-subtle' :
          'status-error-soft border-[var(--status-error)]/30'
        }`}>
          {health.status === 'ok' ? <Globe size={16}/> :
           health.status === 'disabled' ? <Server size={16}/> : <AlertCircle size={16}/>}
          <span className="font-medium">
            Postiz {health.status === 'ok' ? 'connected' : health.status === 'disabled' ? 'disabled' : 'unreachable'}
          </span>
          {health.mode && health.mode !== 'disabled' && (
            <span className="text-xs opacity-75">({health.mode})</span>
          )}
          {health.error && <span className="text-xs opacity-75">— {health.error}</span>}
        </div>
      )}

      {health?.status === 'disabled' && (
        <div className="rounded-lg border border-[var(--status-warning)]/30 status-warning-soft p-4 text-sm">
          <p className="font-medium">Social publishing is disabled</p>
          <p className="mt-1">
            Set <code className="bg-white px-1 rounded">POSTIZ_MODE=self_hosted</code> or{' '}
            <code className="bg-white px-1 rounded">POSTIZ_MODE=cloud</code> in your backend env,
            then configure <code className="bg-white px-1 rounded">POSTIZ_API_URL</code> and{' '}
            <code className="bg-white px-1 rounded">POSTIZ_API_KEY</code>.
          </p>
        </div>
      )}

      {loading ? (
        <div className="text-sm text-muted-foreground">Loading integrations…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {PLATFORMS.map((plat) => (
            <PlatformCard
              key={plat.key}
              plat={plat}
              existing={integrations.find((i) => i.platform === plat.key)}
              onSave={save}
              onRemove={remove}
              saving={saving}
            />
          ))}
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-1">
        <p className="font-medium">How to connect:</p>
        <ol className="list-decimal list-inside space-y-0.5">
          <li>Open your Postiz instance (UI or cloud dashboard)</li>
          <li>Go to <strong>Integrations</strong> → add the platform you want</li>
          <li>Complete OAuth in the popup</li>
          <li>Copy the <strong>Integration ID</strong> shown after connection</li>
          <li>Paste it above and click Connect</li>
        </ol>
      </div>
    </div>
  )
}
