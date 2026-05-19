'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Check, Sparkles, Archive, Loader2, Eye, RefreshCw } from 'lucide-react'
import { GenerateVisualButton } from '@/components/content-hub/generate-visual-button'

interface DraftCardProps {
  draft: {
    id: string
    title: string | null
    body: string | null
    platform: string
    content_type: string
    status: string
    version: number | null
    god_mode_result: unknown
    created_at: string | null
    media_urls: string[] | null
  }
  onAction: (id: string, action: string) => void
  onMediaChange?: () => void
}

function platformClass(platform: string): string {
  const map: Record<string, string> = {
    linkedin: 'platform-linkedin',
    x: 'platform-x',
    instagram: 'platform-instagram',
    facebook: 'platform-facebook',
    tiktok: 'platform-tiktok',
    blog: 'platform-blog',
    email: 'platform-email',
  }
  return map[platform] || 'platform-x'
}

function statusVariant(status: string) {
  switch (status) {
    case 'approved': return 'default' as const
    case 'published': return 'default' as const
    case 'scheduled': return 'secondary' as const
    case 'archived': return 'secondary' as const
    case 'god_mode': return 'outline' as const
    default: return 'outline' as const
  }
}

export function DraftCard({ draft, onAction, onMediaChange }: DraftCardProps) {
  const godResult = draft.god_mode_result as { verdict?: string; advocate_score?: number } | null
  const firstMedia = draft.media_urls?.[0]
  const [pendingAction, setPendingAction] = useState<string | null>(null)

  const handle = async (action: string) => {
    setPendingAction(action)
    try { await onAction(draft.id, action) } finally { setPendingAction(null) }
  }

  const isTerminal = draft.status === 'published' || draft.status === 'archived'
  const isApproved = draft.status === 'approved' || draft.status === 'scheduled'

  // Notion pastel tint strip by status
  const statusBorderColor =
    draft.status === 'approved' || draft.status === 'scheduled' ? 'var(--tint-approved)' :
    draft.status === 'published' ? 'var(--tint-published)' :
    draft.status === 'archived' ? 'var(--tint-review)' : undefined

  return (
    <Card
      className="flex flex-col border-hairline relative overflow-hidden"
      style={statusBorderColor ? { borderLeftColor: statusBorderColor, borderLeftWidth: '3px' } : undefined}
    >
      <CardContent className="pt-4 space-y-3 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2">
          <div className="flex gap-1.5 flex-wrap">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${platformClass(draft.platform)}`}>
              {draft.platform.toUpperCase()}
            </span>
            <Badge variant="secondary" className="text-[11px]">
              {draft.content_type}
            </Badge>
          </div>
          <Badge variant={statusVariant(draft.status)} className="text-[11px]">
            {draft.status.toUpperCase().replace('_', ' ')}
          </Badge>
        </div>

        {firstMedia && (
          <div className="rounded-md overflow-hidden border border-hairline">
            <img src={firstMedia} alt="Generated visual" className="w-full h-32 object-cover" />
          </div>
        )}

        <Link href={`/content-hub/${draft.id}`} className="block hover:opacity-80 transition-opacity flex-1">
          <h3 className="font-medium text-sm text-ink line-clamp-2">{draft.title || 'Untitled'}</h3>
          <p className="text-xs text-ink-muted mt-1 line-clamp-3">
            {draft.body?.slice(0, 200) || ''}
          </p>
        </Link>

        {godResult?.verdict && (
          <div className="text-xs">
            <span className="text-ink-subtle">GOD Review:</span>{' '}
            <span className={godResult.verdict === 'pass' ? 'text-status-success font-medium' : 'text-status-warning font-medium'}>
              {godResult.verdict.toUpperCase()}
            </span>
            {godResult.advocate_score != null && (
              <span className="text-ink-subtle"> · {godResult.advocate_score}/10</span>
            )}
          </div>
        )}

        {/* Action bar */}
        <div className="flex items-center gap-1.5 pt-2 border-t border-hairline flex-wrap">
          <Link href={`/content-hub/${draft.id}`} className="shrink-0">
            <Button variant="ghost" size="xs" title="Open draft">
              <Eye className="size-3" />
              View
            </Button>
          </Link>

          {!isTerminal && !isApproved && (
            <Button
              variant="default"
              size="xs"
              onClick={() => handle('approved')}
              disabled={pendingAction !== null}
              className="bg-[var(--status-success)] hover:bg-[var(--status-success)]/90 text-white"
              title="Approve this draft"
            >
              {pendingAction === 'approved'
                ? <Loader2 className="size-3 animate-spin" />
                : <Check className="size-3" />}
              Approve
            </Button>
          )}

          {isApproved && (
            <Button
              variant="outline"
              size="xs"
              onClick={() => handle('draft')}
              disabled={pendingAction !== null}
              title="Move back to draft"
            >
              {pendingAction === 'draft'
                ? <Loader2 className="size-3 animate-spin" />
                : <RefreshCw className="size-3" />}
              Revert
            </Button>
          )}

          {!isTerminal && (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => handle('god_mode')}
              disabled={pendingAction !== null}
              title="Run 4-agent GOD mode review"
            >
              {pendingAction === 'god_mode'
                ? <Loader2 className="size-3 animate-spin" />
                : <Sparkles className="size-3 text-brand-accent" />}
              GOD
            </Button>
          )}

          <GenerateVisualButton
            draftId={draft.id}
            platform={draft.platform}
            onGenerated={() => onMediaChange?.()}
          />

          {!isTerminal && (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => handle('archived')}
              disabled={pendingAction !== null}
              className="ml-auto text-ink-subtle hover:text-status-error"
              title="Archive this draft"
            >
              {pendingAction === 'archived'
                ? <Loader2 className="size-3 animate-spin" />
                : <Archive className="size-3" />}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
