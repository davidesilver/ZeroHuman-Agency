'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Settings as SettingsIcon, Key, Bot, Mail, Share2, Database, Clock, Building, Plus, Loader2, ExternalLink, Brain } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'
import Link from 'next/link'

const CONFIG_SECTIONS = [
  {
    title: 'API Keys',
    icon: Key,
    items: [
      { key: 'ANTHROPIC_API_KEY', label: 'Claude API', status: 'check' },
      { key: 'OPENROUTER_API_KEY', label: 'OpenRouter', status: 'check' },
      { key: 'SERPER_API_KEY', label: 'Serper (search)', status: 'check' },
      { key: 'YOUTUBE_API_KEY', label: 'YouTube Data', status: 'check' },
      { key: 'RESEND_API_KEY', label: 'Resend (email)', status: 'check' },
    ],
  },
  {
    title: 'LLM Configuration',
    icon: Bot,
    items: [
      { key: 'scoring_model', label: 'Scoring Model', value: 'claude-sonnet-4-20250514' },
      { key: 'auto_approve', label: 'Auto-approve threshold', value: '≥ 8.0' },
      { key: 'auto_reject', label: 'Auto-reject threshold', value: '≤ 3.0' },
    ],
  },
  {
    title: 'Email / Newsletter',
    icon: Mail,
    items: [
      { key: 'from_email', label: 'From email', value: 'newsletter@yourdomain.com' },
      { key: 'from_name', label: 'From name', value: 'Content Engine' },
    ],
  },
  {
    title: 'Social Platforms',
    icon: Share2,
    items: [
      { key: 'linkedin', label: 'LinkedIn', status: 'not_configured' },
      { key: 'twitter', label: 'Twitter/X', status: 'not_configured' },
      { key: 'instagram', label: 'Instagram', status: 'not_configured' },
      { key: 'tiktok', label: 'TikTok', status: 'not_configured' },
    ],
  },
  {
    title: 'Research Pipeline',
    icon: Database,
    items: [
      { key: 'dedup_threshold', label: 'Dedup similarity threshold', value: '0.85' },
      { key: 'max_items', label: 'Max items per retriever', value: '100' },
    ],
  },
  {
    title: 'Scheduler',
    icon: Clock,
    items: [
      { key: 'daily_pipeline', label: 'Daily research pipeline', value: '07:00 CET' },
      { key: 'feedback_loop', label: 'Feedback loop update', value: '02:00 CET' },
      { key: 'publish_scheduled', label: 'Publish scheduled posts', value: 'every 10min' },
    ],
  },
]

function AddBrandCard() {
  const { brands, setActiveBrand } = useBrand()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [topics, setTopics] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleNameChange = (v: string) => {
    setName(v)
    setSlug(v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
  }

  const handleCreate = async () => {
    if (!name.trim() || !slug.trim()) return
    setSaving(true)
    setError(null)
    try {
      const resp = await fetch('/api/brands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          slug: slug.trim(),
          topics: topics ? topics.split(',').map(t => t.trim()).filter(Boolean) : [],
        }),
      })
      const json = await resp.json()
      if (json.success) {
        const newBrand = { id: json.data.id, name: json.data.name, slug: json.data.slug }
        setActiveBrand(newBrand)
        setSuccess(`Brand "${newBrand.name}" created and set as active.`)
        setName(''); setSlug(''); setTopics('')
        setOpen(false)
        window.location.reload()
      } else {
        setError(json.error?.message || 'Failed to create brand')
      }
    } catch {
      setError('Network error')
    }
    setSaving(false)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Building className="size-4 text-muted-foreground" />
            Brands
            <Badge variant="secondary" className="text-[10px] ml-1">{brands.length}</Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Link
              href="/brands"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Manage
            </Link>
            <Button
              size="sm"
              className="h-7 text-xs gap-1 bg-staging-bg hover:bg-staging-bg/90 text-white"
              onClick={() => { setOpen(!open); setError(null) }}
            >
              <Plus className="size-3" /> Add brand
            </Button>
          </div>
        </div>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          <div className="space-y-3 p-3 bg-secondary/40 rounded-md">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Name</Label>
                <Input
                  value={name}
                  onChange={e => handleNameChange(e.target.value)}
                  placeholder="Silvestri Pallets"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Slug <span className="text-muted-foreground">(auto)</span></Label>
                <Input
                  value={slug}
                  onChange={e => setSlug(e.target.value)}
                  placeholder="silvestri-pallets"
                  className="h-8 text-sm"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Topics <span className="text-muted-foreground">(comma separated)</span></Label>
              <Input
                value={topics}
                onChange={e => setTopics(e.target.value)}
                placeholder="logistics, sustainability, B2B"
                className="h-8 text-sm"
              />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            {success && <p className="text-xs text-green-600">{success}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs bg-staging-bg hover:bg-staging-bg/90 text-white"
                disabled={saving || !name.trim() || !slug.trim()}
                onClick={handleCreate}
              >
                {saving ? <Loader2 className="size-3 animate-spin" /> : null}
                {saving ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Badge variant="outline" className="text-xs">
          <SettingsIcon className="size-3 mr-1" />
          Read-only (edit .env.local)
        </Badge>
      </div>

      {/* Brands — actionable section at the top */}
      <AddBrandCard />

      {/* Brand Context — quick link to memory management */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="size-4 text-muted-foreground" />
              Brand Context Memory
            </CardTitle>
            <Link
              href="/settings/brand-context"
              className="inline-flex items-center gap-1 h-7 px-2.5 text-xs rounded-lg
                         hover:bg-muted hover:text-foreground transition-colors text-muted-foreground"
            >
              <ExternalLink className="size-3" /> Manage
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-xs text-muted-foreground">
            Tone rules, principles, gold examples and discard examples stored in semantic memory
            and automatically loaded by all AI agents.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {CONFIG_SECTIONS.map(section => (
          <Card key={section.title}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <section.icon className="size-4 text-muted-foreground" />
                {section.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {section.items.map(item => (
                  <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{item.label}</span>
                      <code className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">{item.key}</code>
                    </div>
                    <div>
                      {'status' in item && item.status === 'check' && (
                        <Badge variant="outline" className="text-[10px] text-amber-600">Check .env.local</Badge>
                      )}
                      {'status' in item && item.status === 'configured' && (
                        <Badge className="text-[10px] bg-green-600">Configured</Badge>
                      )}
                      {'status' in item && item.status === 'not_configured' && (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground">Not configured</Badge>
                      )}
                      {'value' in item && (
                        <span className="text-sm font-mono text-muted-foreground">{item.value}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
