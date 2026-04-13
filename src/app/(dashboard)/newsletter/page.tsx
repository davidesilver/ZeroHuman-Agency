'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Plus, Send, Eye, Check, Loader2 } from 'lucide-react'

export default function NewsletterPage() {
  const [newsletters, setNewsletters] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [previewId, setPreviewId] = useState<string | null>(null)

  const fetchNewsletters = useCallback(async () => {
    setIsLoading(true)
    try {
      const resp = await fetch('/api/newsletter?per_page=50')
      const json = await resp.json()
      if (json.success) setNewsletters(json.data.newsletters || [])
    } catch {}
    setIsLoading(false)
  }, [])

  useEffect(() => { fetchNewsletters() }, [fetchNewsletters])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const resp = await fetch('/api/newsletter/generate', { method: 'POST' })
      const json = await resp.json()
      if (json.success) {
        await fetchNewsletters()
      }
    } catch {}
    setGenerating(false)
  }

  const handlePreview = async (id: string) => {
    setPreviewId(id)
    try {
      const resp = await fetch(`/api/newsletter/${id}/preview`)
      const json = await resp.json()
      if (json.success) {
        setPreviewHtml(json.data.html)
      }
    } catch {}
  }

  const handleApprove = async (id: string) => {
    try {
      await fetch(`/api/newsletter/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'approved' }),
      })
      await fetchNewsletters()
    } catch {}
  }

  const handleSend = async (id: string) => {
    const confirmed = window.confirm('Send this newsletter? This action cannot be undone.')
    if (!confirmed) return

    setSendingId(id)
    try {
      await fetch('/api/newsletter/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ newsletter_id: id, recipients: [] }),
      })
      await fetchNewsletters()
    } catch {}
    setSendingId(null)
  }

  const closePreview = () => {
    setPreviewHtml(null)
    setPreviewId(null)
  }

  const statusVariant = (status: string) => {
    switch (status) {
      case 'sent': return 'default' as const
      case 'approved': return 'default' as const
      case 'scheduled': return 'secondary' as const
      default: return 'outline' as const
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Newsletter</h1>
        <Button
          className="bg-staging-bg hover:bg-staging-bg/90 text-white"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Plus className="size-4" />
          )}
          {generating ? 'Generating...' : 'Generate Newsletter'}
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="Sent this month" value={newsletters.filter(n => n.status === 'sent').length} />
        <KPICard title="Avg open rate" value="—" subtitle="Data incoming" />
        <KPICard title="Subscribers" value="—" subtitle="Connect ESP" />
        <KPICard title="Avg CTR" value="—" subtitle="Data incoming" />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : newsletters.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No newsletters yet. Click &quot;Generate Newsletter&quot; to get started.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">#</TableHead>
              <TableHead>Title</TableHead>
              <TableHead className="w-28">Date</TableHead>
              <TableHead className="w-24">Open Rate</TableHead>
              <TableHead className="w-20">CTR</TableHead>
              <TableHead className="w-24">Status</TableHead>
              <TableHead className="w-36">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {newsletters.map((nl) => (
              <TableRow key={nl.id}>
                <TableCell className="font-medium">{nl.edition_number}</TableCell>
                <TableCell>{nl.title}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {nl.sent_at ? new Date(nl.sent_at).toLocaleDateString('en-US') : '—'}
                </TableCell>
                <TableCell>{nl.open_rate ? `${(nl.open_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>{nl.click_rate ? `${(nl.click_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(nl.status)} className="text-[10px]">
                    {nl.status.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => handlePreview(nl.id)}
                      title="Preview"
                    >
                      <Eye className="size-3" />
                    </Button>
                    {nl.status === 'draft' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-green-600"
                        onClick={() => handleApprove(nl.id)}
                        title="Approve"
                      >
                        <Check className="size-3" />
                      </Button>
                    )}
                    {(nl.status === 'approved' || nl.status === 'draft') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-brand-primary"
                        onClick={() => handleSend(nl.id)}
                        disabled={sendingId === nl.id}
                        title="Send"
                      >
                        {sendingId === nl.id ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <Send className="size-3" />
                        )}
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Preview Modal */}
      {previewHtml && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-medium">Newsletter Preview</h3>
              <Button variant="ghost" size="sm" onClick={closePreview}>
                ✕
              </Button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <iframe
                srcDoc={previewHtml}
                className="w-full h-full min-h-[500px] border-0 rounded"
                title="Newsletter Preview"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
