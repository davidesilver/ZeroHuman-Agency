'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Save, Eye, Send, Loader2, Mail, BarChart2, RefreshCw } from 'lucide-react'
import Link from 'next/link'

interface NewsletterDraft {
  id: string
  title: string | null
  edition_number: number | null
  status: string
  html_body: string | null
  created_at: string
  layout_type: string | null
  subject_variant_a: string | null
  subject_variant_b: string | null
  open_rate: number | null
  click_rate: number | null
}

interface Report {
  sent: number
  delivered: number
  opens: number
  unique_opens: number
  clicks: number
  unique_clicks: number
  unsubscribes: number
  bounces: number
  open_rate: number
  click_rate: number
  click_to_open: number
}

export default function NewsletterEditPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [draft, setDraft] = useState<NewsletterDraft | null>(null)
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [reportLoading, setReportLoading] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch(`/api/newsletter/${id}`)
        const json = await resp.json()
        if (json.success && json.data) {
          setDraft(json.data)
          setTitle(json.data.title || '')
        }
      } catch {}
      setLoading(false)
    }
    if (id) load()
  }, [id])

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const resp = await fetch(`/api/newsletter/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
      const json = await resp.json()
      if (json.success) {
        setMsg('✅ Saved')
        setDraft(prev => prev ? { ...prev, title } : prev)
      } else {
        setMsg(`❌ ${json.error?.message || 'Save failed'}`)
      }
    } catch {
      setMsg('❌ Network error')
    }
    setSaving(false)
  }

  const handlePreview = async () => {
    try {
      const resp = await fetch(`/api/newsletter/${id}/preview`)
      const json = await resp.json()
      if (json.success) setPreviewHtml(json.data.html)
    } catch {}
  }

  const handleApprove = async () => {
    try {
      const resp = await fetch(`/api/newsletter/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'approved' }),
      })
      const json = await resp.json()
      if (json.success) {
        setDraft(prev => prev ? { ...prev, status: 'approved' } : prev)
        setMsg('✅ Approved — ready to send')
      }
    } catch {}
  }

  const fetchReport = async () => {
    setReportLoading(true)
    try {
      const resp = await fetch(`/api/newsletter/${id}/report`)
      const json = await resp.json()
      if (json.success) setReport(json.data)
    } catch {}
    setReportLoading(false)
  }

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!draft) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        Newsletter not found.{' '}
        <Link href="/newsletter" className="underline">Back to list</Link>
      </div>
    )
  }

  return (
    <div className="space-y-5 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/newsletter" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Mail className="size-5" />
              Newsletter #{draft.edition_number}
              {draft.layout_type && (
                <span className="text-xs font-normal text-muted-foreground uppercase tracking-wide ml-1">
                  {draft.layout_type}
                </span>
              )}
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Created {new Date(draft.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
            </p>
          </div>
        </div>
        <Badge variant={draft.status === 'approved' ? 'default' : 'outline'} className="text-xs">
          {draft.status.toUpperCase()}
        </Badge>
      </div>

      {/* Title edit */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Title</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="flex-1"
              placeholder="Newsletter title…"
            />
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="gap-1.5"
            >
              {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
          {msg && <p className="text-xs mt-2 text-muted-foreground">{msg}</p>}
        </CardContent>
      </Card>

      {/* Subject variants */}
      {(draft.subject_variant_a || draft.subject_variant_b) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">A/B Subject Lines</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {draft.subject_variant_a && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-muted-foreground w-4">A</span>
                <span className="text-sm">{draft.subject_variant_a}</span>
              </div>
            )}
            {draft.subject_variant_b && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-muted-foreground w-4">B</span>
                <span className="text-sm text-muted-foreground">{draft.subject_variant_b}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* HTML preview */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Content</CardTitle>
            <Button variant="outline" size="sm" onClick={handlePreview} className="gap-1.5 h-7 text-xs">
              <Eye className="size-3.5" /> Preview HTML
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {draft.html_body ? (
            <pre className="text-[11px] bg-secondary/40 rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap text-muted-foreground">
              {draft.html_body.slice(0, 1200)}{draft.html_body.length > 1200 ? '\n…' : ''}
            </pre>
          ) : (
            <p className="text-xs text-muted-foreground italic">No HTML body yet.</p>
          )}
        </CardContent>
      </Card>

      {/* Analytics (sent newsletters only) */}
      {draft.status === 'sent' && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-1.5">
                <BarChart2 className="size-4" /> Analytics
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchReport}
                disabled={reportLoading}
                className="gap-1.5 h-7 text-xs"
              >
                {reportLoading
                  ? <Loader2 className="size-3.5 animate-spin" />
                  : <RefreshCw className="size-3.5" />}
                {reportLoading ? 'Loading…' : 'Fetch from provider'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {report ? (
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: 'Sent', value: report.sent },
                  { label: 'Delivered', value: report.delivered },
                  { label: 'Open rate', value: pct(report.open_rate) },
                  { label: 'Click rate', value: pct(report.click_rate) },
                  { label: 'Unique opens', value: report.unique_opens },
                  { label: 'Unique clicks', value: report.unique_clicks },
                  { label: 'CTOR', value: pct(report.click_to_open) },
                  { label: 'Unsubscribes', value: report.unsubscribes },
                ].map(({ label, value }) => (
                  <div key={label} className="text-center p-3 bg-secondary/30 rounded-lg">
                    <div className="text-lg font-bold">{value}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Click &quot;Fetch from provider&quot; to load live analytics.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {draft.status === 'draft' && (
          <Button onClick={handleApprove} size="sm" className="gap-1.5 bg-green-600 hover:bg-green-700 text-white">
            <Send className="size-3.5" /> Approve for sending
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={() => router.push('/newsletter')}>
          Back to list
        </Button>
      </div>

      {/* Preview modal */}
      {previewHtml && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-medium text-sm">HTML Preview</h3>
              <Button variant="ghost" size="sm" onClick={() => setPreviewHtml(null)}>✕</Button>
            </div>
            <div className="flex-1 overflow-auto">
              <iframe srcDoc={previewHtml} className="w-full h-full min-h-[500px] border-0" title="Preview" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
