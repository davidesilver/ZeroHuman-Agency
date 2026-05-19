'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Key, Trash2, Loader2, CheckCircle2, AlertCircle, ExternalLink,
  Eye, EyeOff, Wifi, WifiOff, ChevronDown, ChevronUp, Server,
} from 'lucide-react'
import { useBrand } from '@/lib/brand-context'

// ── Types ──────────────────────────────────────────────────────────────────────

interface ProviderDef {
  id: string
  display_name: string
  category: 'direct' | 'gateway' | 'meta_router'
  api_type: 'openai_compatible' | 'anthropic_native'
  auth_type: 'api_key' | 'none' | 'optional_key'
  billing_model: string
  base_url_editable: boolean
  default_base_url: string
  models: string[]
  priority: number
  docs_url: string
  logo: string
  configured?: boolean
}

interface GatewayState {
  url: string
  probing: boolean
  online: boolean | null
  models: string[]
  latency_ms: number | null
  error: string | null
}

interface KeyState {
  value: string
  visible: boolean
  saving: boolean
  testing: boolean
  removing: boolean
  status: 'idle' | 'ok' | 'error'
  message: string
  latency_ms: number | null
  models: string[]
}

const PROVIDER_ICONS: Record<string, string> = {
  anthropic: '🔷',
  openai: '🟢',
  google: '🔴',
  groq: '⚡',
  deepseek: '🔵',
  mistral: '🌊',
  xai: '✖',
  together: '🤝',
  fireworks: '🎆',
  nvidia: '🟩',
  perplexity: '🔍',
  moonshot: '🌙',
  cerebras: '🧠',
  sambanova: '🔶',
  qwen: '☁️',
  ollama: '🦙',
  openclaw: '🦎',
  lmstudio: '🖥️',
  vllm: '⚙️',
  litellm: '🔀',
  cloudflare: '☁️',
  openrouter: '🌐',
}

const BILLING_LABELS: Record<string, string> = {
  pay_per_use: 'Pay-per-use',
  subscription: 'Subscription',
  free: 'Free',
  self_hosted: 'Self-hosted',
  prepaid: 'Prepaid',
}

const SECTION_TITLES: Record<string, string> = {
  direct: 'Direct Providers',
  gateway: 'Local Gateways',
  meta_router: 'Meta-Routers',
}

// ── Key card ───────────────────────────────────────────────────────────────────

function ProviderKeyCard({
  provider,
  onConfiguredChange,
}: {
  provider: ProviderDef
  onConfiguredChange: (id: string, configured: boolean) => void
}) {
  const { activeBrand } = useBrand()
  const [ks, setKs] = useState<KeyState>({
    value: '',
    visible: false,
    saving: false,
    testing: false,
    removing: false,
    status: 'idle',
    message: '',
    latency_ms: null,
    models: [],
  })
  const [showModels, setShowModels] = useState(false)
  const isConfigured = provider.configured ?? false

  function merge(patch: Partial<KeyState>) {
    setKs(prev => ({ ...prev, ...patch }))
  }

  async function handleTest() {
    if (!ks.value.trim()) return
    merge({ testing: true, status: 'idle', message: '' })
    try {
      const res = await fetch(`/api/llm/providers/${provider.id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: ks.value.trim() }),
      })
      const json = await res.json()
      if (json.valid) {
        merge({
          status: 'ok',
          message: `Valid — ${json.latency_ms}ms`,
          latency_ms: json.latency_ms,
          models: json.models ?? [],
        })
      } else {
        merge({ status: 'error', message: json.error || 'Key rejected' })
      }
    } catch {
      merge({ status: 'error', message: 'Network error' })
    } finally {
      merge({ testing: false })
    }
  }

  async function handleSave() {
    if (!ks.value.trim()) return
    merge({ saving: true, status: 'idle', message: '' })
    try {
      const res = await fetch(`/api/llm/providers/${provider.id}/key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: ks.value.trim() }),
      })
      const json = await res.json()
      if (res.ok && json.valid) {
        merge({
          status: 'ok',
          message: `Saved — ${json.latency_ms}ms`,
          latency_ms: json.latency_ms,
          models: json.models ?? [],
          value: '',
        })
        onConfiguredChange(provider.id, true)
      } else {
        const msg = json.detail || json.error?.message || 'Save failed'
        merge({ status: 'error', message: msg })
      }
    } catch {
      merge({ status: 'error', message: 'Network error' })
    } finally {
      merge({ saving: false })
    }
  }

  async function handleRemove() {
    merge({ removing: true })
    try {
      await fetch(`/api/llm/providers/${provider.id}/key`, { method: 'DELETE' })
      merge({ status: 'idle', message: '', models: [], latency_ms: null })
      onConfiguredChange(provider.id, false)
    } catch {
      // best-effort
    } finally {
      merge({ removing: false })
    }
  }

  const busy = ks.saving || ks.testing || ks.removing

  return (
    <Card className="border border-border/60">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xl">{PROVIDER_ICONS[provider.id] ?? '🤖'}</span>
            <div>
              <CardTitle className="text-sm font-semibold">{provider.display_name}</CardTitle>
              <p className="text-xs text-muted-foreground">{BILLING_LABELS[provider.billing_model] ?? provider.billing_model}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap justify-end">
            {isConfigured && (
              <Badge variant="default" className="bg-green-600/90 text-white text-xs">Configured</Badge>
            )}
            {provider.docs_url && (
              <a href={provider.docs_url} target="_blank" rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
                title="Get API key">
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Key input */}
        {provider.auth_type !== 'none' && (
          <div className="space-y-1.5">
            <Label className="text-xs">
              {isConfigured ? 'Replace API key' : 'API key'}
              {provider.auth_type === 'optional_key' && (
                <span className="text-muted-foreground ml-1">(optional)</span>
              )}
            </Label>
            <div className="relative">
              <Input
                type={ks.visible ? 'text' : 'password'}
                value={ks.value}
                onChange={e => merge({ value: e.target.value, status: 'idle', message: '' })}
                placeholder={isConfigured ? '••••••••••••• (leave blank to keep current)' : 'sk-…'}
                className="pr-8 font-mono text-xs"
                onKeyDown={e => { if (e.key === 'Enter' && ks.value) handleSave() }}
              />
              <button
                type="button"
                onClick={() => merge({ visible: !ks.visible })}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {ks.visible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        )}

        {/* Status feedback */}
        {ks.status !== 'idle' && (
          <div className={`flex items-center gap-1.5 text-xs ${ks.status === 'ok' ? 'text-green-600' : 'text-destructive'}`}>
            {ks.status === 'ok'
              ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              : <AlertCircle className="h-3.5 w-3.5 shrink-0" />}
            <span>{ks.message}</span>
          </div>
        )}

        {/* Models disclosure */}
        {ks.models.length > 0 && (
          <div>
            <button
              onClick={() => setShowModels(v => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {showModels ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {ks.models.length} models available
            </button>
            {showModels && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {ks.models.slice(0, 20).map(m => (
                  <Badge key={m} variant="outline" className="text-xs font-mono">{m}</Badge>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {provider.auth_type !== 'none' && ks.value.trim() && (
            <>
              <Button size="sm" variant="outline" onClick={handleTest} disabled={busy} className="h-7 text-xs">
                {ks.testing ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Key className="h-3 w-3 mr-1" />}
                Test
              </Button>
              <Button size="sm" onClick={handleSave} disabled={busy} className="h-7 text-xs">
                {ks.saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                Save key
              </Button>
            </>
          )}
          {isConfigured && (
            <Button size="sm" variant="ghost" onClick={handleRemove} disabled={busy}
              className="h-7 text-xs text-destructive hover:text-destructive hover:bg-destructive/10 ml-auto">
              {ks.removing ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Trash2 className="h-3 w-3 mr-1" />}
              Remove
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ── Gateway card ───────────────────────────────────────────────────────────────

function GatewayCard({ provider }: { provider: ProviderDef }) {
  const [gs, setGs] = useState<GatewayState>({
    url: provider.default_base_url,
    probing: false,
    online: null,
    models: [],
    latency_ms: null,
    error: null,
  })
  const [showModels, setShowModels] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [keyVisible, setKeyVisible] = useState(false)

  function merge(patch: Partial<GatewayState>) {
    setGs(prev => ({ ...prev, ...patch }))
  }

  // Strip /v1 suffix for the probe endpoint — backend appends /models itself
  function baseUrlForProbe(url: string) {
    return url.replace(/\/v1\/?$/, '')
  }

  async function saveUrl() {
    try {
      await fetch(`/api/llm/gateways/${provider.id}/url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: gs.url }),
      })
    } catch {
      // best-effort
    }
  }

  async function probe() {
    merge({ probing: true, online: null, error: null, models: [] })
    try {
      const res = await fetch('/api/llm/gateways/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: baseUrlForProbe(gs.url) }),
      })
      const json = await res.json()
      if (res.ok) {
        merge({ online: json.online, models: json.models ?? [], latency_ms: json.latency_ms, error: json.error ?? null })
      } else {
        merge({ online: false, error: json.detail || json.error?.message || 'Probe failed' })
      }
    } catch {
      merge({ online: false, error: 'Network error' })
    } finally {
      merge({ probing: false })
    }
  }

  return (
    <Card className="border border-border/60">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{PROVIDER_ICONS[provider.id] ?? '🖥️'}</span>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              {provider.display_name}
              <Badge variant="outline" className="text-xs">Local</Badge>
            </CardTitle>
            <p className="text-xs text-muted-foreground truncate">{gs.url}</p>
          </div>
          {gs.online !== null && (
            gs.online
              ? <Wifi className="h-4 w-4 text-green-600 shrink-0" />
              : <WifiOff className="h-4 w-4 text-destructive shrink-0" />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {provider.base_url_editable && (
          <div className="space-y-1.5">
            <Label className="text-xs">Gateway URL</Label>
            <Input
              value={gs.url}
              onChange={e => merge({ url: e.target.value })}
              className="font-mono text-xs"
              placeholder="http://localhost:11434/v1"
            />
          </div>
        )}

        {provider.auth_type === 'optional_key' && (
          <div className="space-y-1.5">
            <Label className="text-xs">API key <span className="text-muted-foreground">(optional)</span></Label>
            <div className="relative">
              <Input
                type={keyVisible ? 'text' : 'password'}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="leave blank for no auth"
                className="pr-8 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setKeyVisible(v => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {keyVisible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        )}

        {/* Probe status */}
        {gs.online !== null && (
          <div className={`flex items-center gap-1.5 text-xs ${gs.online ? 'text-green-600' : 'text-destructive'}`}>
            {gs.online
              ? <><CheckCircle2 className="h-3.5 w-3.5 shrink-0" />{gs.models.length} models — {gs.latency_ms}ms</>
              : <><AlertCircle className="h-3.5 w-3.5 shrink-0" />{gs.error ?? 'Offline'}</>}
          </div>
        )}

        {gs.online && gs.models.length > 0 && (
          <div>
            <button
              onClick={() => setShowModels(v => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {showModels ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              Show models
            </button>
            {showModels && (
              <div className="mt-1.5 flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                {gs.models.map(m => (
                  <Badge key={m} variant="outline" className="text-xs font-mono">{m}</Badge>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          <Button size="sm" variant="outline" onClick={probe} disabled={gs.probing} className="h-7 text-xs">
            {gs.probing
              ? <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              : <Server className="h-3 w-3 mr-1" />}
            Probe
          </Button>
          {provider.base_url_editable && gs.url !== provider.default_base_url && (
            <Button size="sm" onClick={saveUrl} disabled={gs.probing} className="h-7 text-xs">
              Save URL
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ── Auto-discover button ───────────────────────────────────────────────────────

function AutoDiscoverButton() {
  const [scanning, setScanning] = useState(false)
  const [results, setResults] = useState<Array<{ id: string; display_name: string; online: boolean; models: string[]; latency_ms: number }> | null>(null)

  async function discover() {
    setScanning(true)
    setResults(null)
    try {
      const res = await fetch('/api/llm/gateways/auto-discover')
      const json = await res.json()
      setResults(Array.isArray(json) ? json : [])
    } catch {
      setResults([])
    } finally {
      setScanning(false)
    }
  }

  const online = results?.filter(r => r.online) ?? []

  return (
    <div className="flex items-center gap-2">
      {results && (
        <span className="text-xs text-muted-foreground">
          {online.length > 0
            ? `${online.map(r => r.display_name).join(', ')} online`
            : 'No gateways detected'}
        </span>
      )}
      <Button size="sm" variant="outline" onClick={discover} disabled={scanning} className="h-7 text-xs">
        {scanning ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Wifi className="h-3 w-3 mr-1" />}
        Auto-detect
      </Button>
    </div>
  )
}

// ── Main hub ───────────────────────────────────────────────────────────────────

export function LLMProviderHub({ wizardMode = false }: { wizardMode?: boolean }) {
  const { activeBrand } = useBrand()
  const [providers, setProviders] = useState<ProviderDef[]>([])
  const [loading, setLoading] = useState(true)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    if (!activeBrand?.id) return
    Promise.all([
      fetch('/api/llm/providers/catalog').then(r => r.json()),
      fetch('/api/llm/providers/configured').then(r => r.json()),
    ]).then(([catalog, configured]) => {
      const configuredIds = new Set<string>(
        (Array.isArray(configured) ? configured : [])
          .filter((p: { configured: boolean }) => p.configured)
          .map((p: { id: string }) => p.id)
      )
      const list: ProviderDef[] = (Array.isArray(catalog) ? catalog : []).map(
        (p: ProviderDef) => ({ ...p, configured: configuredIds.has(p.id) })
      )
      setProviders(list)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [activeBrand?.id])

  function handleConfiguredChange(id: string, configured: boolean) {
    setProviders(prev => prev.map(p => p.id === id ? { ...p, configured } : p))
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-8">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading providers…</span>
      </div>
    )
  }

  const directP0 = providers.filter(p => p.category === 'direct' && p.priority === 0)
  const directP1P2 = providers.filter(p => p.category === 'direct' && p.priority > 0)
  const gateways = providers.filter(p => p.category === 'gateway')
  const metaRouters = providers.filter(p => p.category === 'meta_router')

  const configuredCount = providers.filter(p => p.configured).length

  return (
    <div className="space-y-8">
      {/* Summary */}
      <div className="flex items-center gap-3">
        <Badge variant={configuredCount > 0 ? 'default' : 'secondary'} className="text-sm px-3 py-1">
          {configuredCount} provider{configuredCount !== 1 ? 's' : ''} configured
        </Badge>
        <p className="text-sm text-muted-foreground">
          Add your own API keys to use any provider directly.
        </p>
      </div>

      {/* P0 Direct providers */}
      <section>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          Direct Providers
          <Badge variant="outline" className="text-xs">Recommended</Badge>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {directP0.map(p => (
            <ProviderKeyCard key={p.id} provider={p} onConfiguredChange={handleConfiguredChange} />
          ))}
        </div>
      </section>

      {/* P1/P2 Direct providers (collapsible) */}
      {directP1P2.length > 0 && (
        <section>
          <button
            onClick={() => setShowAll(v => !v)}
            className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3 hover:text-primary transition-colors"
          >
            {showAll ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            More Providers
            <Badge variant="secondary" className="text-xs">{directP1P2.length}</Badge>
            {directP1P2.filter(p => p.configured).length > 0 && (
              <Badge variant="default" className="bg-green-600/90 text-white text-xs">
                {directP1P2.filter(p => p.configured).length} configured
              </Badge>
            )}
          </button>
          {showAll && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {directP1P2.map(p => (
                <ProviderKeyCard key={p.id} provider={p} onConfiguredChange={handleConfiguredChange} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Gateways */}
      {gateways.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-foreground">Local Gateways</h3>
            <AutoDiscoverButton />
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            Self-hosted models running on your machine or local network.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {gateways.map(p => (
              <GatewayCard key={p.id} provider={p} />
            ))}
          </div>
        </section>
      )}

      {/* Meta-routers */}
      {metaRouters.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-foreground mb-1">Meta-Routers</h3>
          <p className="text-xs text-muted-foreground mb-3">
            Single API key giving access to 200+ models across all providers.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {metaRouters.map(p => (
              <ProviderKeyCard key={p.id} provider={p} onConfiguredChange={handleConfiguredChange} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
