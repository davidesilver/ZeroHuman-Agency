'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Mail, Loader2, CheckCircle2, AlertCircle, ChevronDown } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'

interface ProviderConfig {
  provider: string
  sender_name: string
  sender_email: string
  list_id: string
  ab_split_pct: number
  ab_wait_hours: number
}

interface ContactList {
  list_id: string
  name: string
  total_subscribers: number
}

const PROVIDERS = [
  { value: 'resend', label: 'Resend', description: 'Simple transactional, no list management' },
  { value: 'brevo', label: 'Brevo', description: 'EU-based, A/B testing, contact lists' },
  { value: 'mailchimp', label: 'Mailchimp', description: 'Audience-based, variate campaigns' },
]

const PROVIDER_DOCS: Record<string, string> = {
  brevo: 'https://app.brevo.com/settings/keys/api',
  resend: 'https://resend.com/api-keys',
  mailchimp: 'https://admin.mailchimp.com/account/api/',
}

const AB_PROVIDERS = ['brevo', 'mailchimp']

export function EmailProviderCard() {
  const { activeBrand } = useBrand()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [loadingLists, setLoadingLists] = useState(false)
  const [validationStatus, setValidationStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const [validationError, setValidationError] = useState('')
  const [lists, setLists] = useState<ContactList[]>([])

  const [provider, setProvider] = useState('resend')
  const [apiKey, setApiKey] = useState('')
  const [senderName, setSenderName] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [listId, setListId] = useState('')
  const [abSplitPct, setAbSplitPct] = useState(20)
  const [abWaitHours, setAbWaitHours] = useState(4)

  useEffect(() => {
    if (!activeBrand) return
    setLoading(true)
    fetch('/api/email-provider/config')
      .then(r => r.json())
      .then(res => {
        const d: Partial<ProviderConfig> = res?.data || {}
        if (d.provider) setProvider(d.provider)
        if (d.sender_name) setSenderName(d.sender_name)
        if (d.sender_email) setSenderEmail(d.sender_email)
        if (d.list_id) setListId(d.list_id)
        if (d.ab_split_pct) setAbSplitPct(d.ab_split_pct)
        if (d.ab_wait_hours) setAbWaitHours(d.ab_wait_hours)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [activeBrand?.id])

  async function handleValidate() {
    if (!apiKey) return
    setValidating(true)
    setValidationStatus('idle')
    setValidationError('')
    try {
      const res = await fetch('/api/email-provider/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: apiKey, sender_name: senderName, sender_email: senderEmail }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || 'Validation failed')
      setValidationStatus('ok')
      // Load lists after successful validation
      if (provider !== 'resend') {
        loadLists()
      }
    } catch (e: unknown) {
      setValidationStatus('error')
      setValidationError(e instanceof Error ? e.message : 'Invalid API key')
    } finally {
      setValidating(false)
    }
  }

  async function loadLists() {
    setLoadingLists(true)
    try {
      const res = await fetch('/api/email-provider/lists')
      const data = await res.json()
      setLists(data?.data || [])
    } catch {
      setLists([])
    } finally {
      setLoadingLists(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await fetch('/api/email-provider/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          sender_name: senderName,
          sender_email: senderEmail,
          list_id: listId,
          ab_split_pct: abSplitPct,
          ab_wait_hours: abWaitHours,
        }),
      })
    } finally {
      setSaving(false)
    }
  }

  const webhookUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/api/webhooks/email/${provider}`
    : `/api/webhooks/email/${provider}`

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Mail className="size-4 text-muted-foreground" />
          Email Provider
          <Badge variant="secondary" className="text-[10px] ml-1">newsletter delivery</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Loading…
          </div>
        ) : (
          <div className="space-y-4">
            {/* Provider selection */}
            <div className="space-y-1.5">
              <Label className="text-xs">Provider</Label>
              <div className="flex gap-2">
                {PROVIDERS.map(p => (
                  <button
                    key={p.value}
                    onClick={() => { setProvider(p.value); setValidationStatus('idle'); setLists([]) }}
                    className={`flex-1 text-left px-3 py-2 rounded-lg border text-xs transition-colors ${
                      provider === p.value
                        ? 'border-primary bg-primary/5 text-foreground'
                        : 'border-border text-muted-foreground hover:border-primary/40'
                    }`}
                  >
                    <div className="font-medium">{p.label}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">{p.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">API Key</Label>
                {PROVIDER_DOCS[provider] && (
                  <a
                    href={PROVIDER_DOCS[provider]}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Get key ↗
                  </a>
                )}
              </div>
              <div className="flex gap-2">
                <Input
                  type="password"
                  value={apiKey}
                  onChange={e => { setApiKey(e.target.value); setValidationStatus('idle') }}
                  placeholder="Paste API key…"
                  className="h-8 text-sm font-mono flex-1"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleValidate}
                  disabled={!apiKey || validating}
                  className="h-8 px-3"
                >
                  {validating ? <Loader2 className="size-3.5 animate-spin" /> : 'Verify'}
                </Button>
              </div>
              {validationStatus === 'ok' && (
                <p className="text-[11px] text-green-600 flex items-center gap-1">
                  <CheckCircle2 className="size-3" /> API key valid
                </p>
              )}
              {validationStatus === 'error' && (
                <p className="text-[11px] text-destructive flex items-center gap-1">
                  <AlertCircle className="size-3" /> {validationError}
                </p>
              )}
            </div>

            {/* Sender */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Sender name</Label>
                <Input
                  value={senderName}
                  onChange={e => setSenderName(e.target.value)}
                  placeholder="My Brand"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Sender email</Label>
                <Input
                  type="email"
                  value={senderEmail}
                  onChange={e => setSenderEmail(e.target.value)}
                  placeholder="newsletter@yourdomain.com"
                  className="h-8 text-sm"
                />
              </div>
            </div>

            {/* List selection (only for providers with list management) */}
            {AB_PROVIDERS.includes(provider) && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Subscriber list</Label>
                  {validationStatus === 'ok' && (
                    <button
                      onClick={loadLists}
                      disabled={loadingLists}
                      className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {loadingLists ? 'Loading…' : 'Refresh lists'}
                    </button>
                  )}
                </div>
                {lists.length > 0 ? (
                  <div className="relative">
                    <select
                      value={listId}
                      onChange={e => setListId(e.target.value)}
                      className="w-full h-8 rounded-md border border-input bg-background px-3 text-sm appearance-none pr-8"
                    >
                      <option value="">Select a list…</option>
                      {lists.map(l => (
                        <option key={l.list_id} value={l.list_id}>
                          {l.name} ({l.total_subscribers.toLocaleString()} subscribers)
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-2 size-4 text-muted-foreground pointer-events-none" />
                  </div>
                ) : (
                  <Input
                    value={listId}
                    onChange={e => setListId(e.target.value)}
                    placeholder={validationStatus === 'ok' ? 'No lists found — enter ID manually' : 'Verify API key to load lists'}
                    className="h-8 text-sm"
                  />
                )}
              </div>
            )}

            {/* A/B settings (only for providers with A/B support) */}
            {AB_PROVIDERS.includes(provider) && (
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">A/B test split %</Label>
                  <Input
                    type="number"
                    min={5}
                    max={50}
                    value={abSplitPct}
                    onChange={e => setAbSplitPct(Number(e.target.value))}
                    className="h-8 text-sm"
                  />
                  <p className="text-[10px] text-muted-foreground">% of list for split (5–50)</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Winner wait (hours)</Label>
                  <Input
                    type="number"
                    min={1}
                    max={168}
                    value={abWaitHours}
                    onChange={e => setAbWaitHours(Number(e.target.value))}
                    className="h-8 text-sm"
                  />
                  <p className="text-[10px] text-muted-foreground">Hours before auto-selecting winner</p>
                </div>
              </div>
            )}

            {/* Webhook URL */}
            {AB_PROVIDERS.includes(provider) && (
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Webhook URL (configure on provider)</Label>
                <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 bg-muted/30">
                  <code className="text-[11px] font-mono text-muted-foreground flex-1 truncate">
                    {webhookUrl}
                  </code>
                  <button
                    onClick={() => navigator.clipboard.writeText(webhookUrl)}
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
                  >
                    Copy
                  </button>
                </div>
              </div>
            )}

            <Button onClick={handleSave} disabled={saving} size="sm" className="w-full">
              {saving ? <><Loader2 className="size-3.5 animate-spin mr-2" /> Saving…</> : 'Save provider settings'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
