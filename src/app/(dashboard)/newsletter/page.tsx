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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Plus, Send, Eye, Check, Loader2, Pencil, Mail } from 'lucide-react'
import Link from 'next/link'

interface Newsletter {
  id: string
  title: string | null
  edition_number: number | null
  status: string
  sent_at: string | null
  open_rate: number | null
  click_rate: number | null
  layout_type: string | null
  subject_variant_b: string | null
}

export default function NewsletterPage() {
  const [newsletters, setNewsletters] = useState<Newsletter[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [generateMsg, setGenerateMsg] = useState<string | null>(null)
  const [sendConfirmOpen, setSendConfirmOpen] = useState(false)
  const [newsletterToSend, setNewsletterToSend] = useState<Newsletter | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)

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
    setGenerateMsg(null)
    try {
      const resp = await fetch('/api/newsletter/generate', { method: 'POST' })
      const json = await resp.json()
      if (json.success) {
        setGenerateMsg(`✅ Draft created: "${json.data?.title || 'Newsletter'}" (edition #${json.data?.edition_number})`)
        await fetchNewsletters()
      } else {
        setGenerateMsg(`❌ ${json.error?.message || 'Generation failed — check approved research items'}`)
      }
    } catch {
      setGenerateMsg('❌ Network error')
    }
    setGenerating(false)
  }

  const handlePreview = async (id: string) => {
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

  const initiateSend = (nl: Newsletter) => {
    setNewsletterToSend(nl)
    setSendError(null)
    setSendConfirmOpen(true)
  }

  const confirmSend = async () => {
    if (!newsletterToSend) return
    const id = newsletterToSend.id
    setSendingId(id)
    setSendError(null)
    try {
      const resp = await fetch('/api/newsletter/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ newsletter_id: id, recipients: [] }),
      })
      const json = await resp.json()
      if (json.success) {
        setSendConfirmOpen(false)
        setNewsletterToSend(null)
        await fetchNewsletters()
      } else {
        setSendError(json.error?.message || 'Failed to send newsletter')
      }
    } catch {
      setSendError('Network error occurred during send')
    }
    setSendingId(null)
  }

  const closePreview = () => {
    setPreviewHtml(null)
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
            <Loader2 className="size-4 animate-spin mr-1" />
          ) : (
            <Plus className="size-4 mr-1" />
          )}
          {generating ? 'Generating…' : 'Generate Newsletter'}
        </Button>
      </div>

      {generateMsg && (
        <p className="text-sm text-muted-foreground -mt-2">{generateMsg}</p>
      )}

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
              <TableHead className="w-24">Layout</TableHead>
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
                <TableCell>
                  <span>{nl.title}</span>
                  {nl.subject_variant_b && (
                    <span className="ml-1.5 text-[9px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 px-1 py-0.5 rounded">A/B</span>
                  )}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground capitalize">{nl.layout_type || '—'}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {nl.sent_at ? new Date(nl.sent_at).toLocaleDateString('en-US') : '—'}
                </TableCell>
                <TableCell>{nl.open_rate ? `${(nl.open_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>{nl.click_rate ? `${(nl.click_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(nl.status)} className="text-[11px]">
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
                      <Link
                        href={`/newsletter/${nl.id}`}
                        className="inline-flex items-center h-7 px-2 text-xs rounded hover:bg-muted transition-colors"
                        title="Edit draft"
                      >
                        <Pencil className="size-3" />
                      </Link>
                    )}
                    {nl.status === 'draft' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-[var(--status-success)]"
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
                        onClick={() => initiateSend(nl)}
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

      {/* Send Confirmation Dialog */}
      <Dialog open={sendConfirmOpen} onOpenChange={setSendConfirmOpen}>
        <DialogContent className="sm:max-w-md border border-brand-primary/20 bg-background/95 backdrop-blur-md">
          <DialogHeader className="flex flex-row items-start gap-3 space-y-0 pb-2">
            <div className="p-2 rounded-full bg-brand-primary/10 text-brand-primary mt-0.5">
              <Mail className="size-5" />
            </div>
            <div className="space-y-1">
              <DialogTitle className="text-lg font-semibold text-brand-primary">
                Send Newsletter
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                This action is permanent and cannot be undone.
              </p>
            </div>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <p className="text-sm">
              Are you sure you want to broadcast <strong className="font-semibold text-foreground">&quot;{newsletterToSend?.title || 'this newsletter'}&quot;</strong>?
            </p>
            <div className="rounded-lg bg-muted/50 border p-3 space-y-1.5 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Campaign Details:</p>
              <ul className="list-disc pl-4 space-y-1">
                <li>Edition number: <span className="font-mono text-foreground">#{newsletterToSend?.edition_number}</span></li>
                <li>Recipients: <span className="text-foreground">All active verified subscribers in your connected ESP</span></li>
                {newsletterToSend?.subject_variant_b && (
                  <li>
                    Subject A/B Testing: <span className="text-blue-500 font-medium font-semibold">Enabled</span> (Variant B: &quot;{newsletterToSend.subject_variant_b}&quot;)
                  </li>
                )}
                <li>Stats tracking: <span className="text-foreground">Real-time Open & Click rates analytics enabled</span></li>
              </ul>
            </div>
            {sendError && (
              <p className="text-xs font-medium text-destructive bg-destructive/5 border border-destructive/10 rounded-md p-2">
                {sendError}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setSendConfirmOpen(false)}
              disabled={!!sendingId}
              className="sm:order-first"
            >
              Cancel
            </Button>
            <Button
              onClick={confirmSend}
              disabled={!!sendingId}
              className="bg-brand-primary hover:bg-brand-primary/90 text-white font-medium flex items-center gap-1.5"
            >
              {sendingId ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              {sendingId ? 'Sending...' : 'Send Now'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
