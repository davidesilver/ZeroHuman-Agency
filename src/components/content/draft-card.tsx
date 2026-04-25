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

function platformColor(platform: string): string {
  const map: Record<string, string> = {
    linkedin: 'bg-blue-100 text-blue-800',
    x: 'bg-gray-100 text-gray-800',
    instagram: 'bg-pink-100 text-pink-800',
    facebook: 'bg-indigo-100 text-indigo-800',
    tiktok: 'bg-purple-100 text-purple-800',
    blog: 'bg-green-100 text-green-800',
    email: 'bg-amber-100 text-amber-800',
  }
  return map[platform] || 'bg-gray-100 text-gray-800'
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

  return (
    <Card className="flex flex-col">
      <CardContent className="pt-4 space-y-3 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2">
          <div className="flex gap-1.5 flex-wrap">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${platformColor(draft.platform)}`}>
              {draft.platform.toUpperCase()}
            </span>
            <Badge variant="secondary" className="text-[10px]">
              {draft.content_type}
            </Badge>
          </div>
          <Badge variant={statusVariant(draft.status)} className="text-[10px]">
            {draft.status.toUpperCase().replace('_', ' ')}
          </Badge>
        </div>

        {firstMedia && (
          <div className="rounded overflow-hidden border">
            <img src={firstMedia} alt="Generated visual" className="w-full h-32 object-cover" />
          </div>
        )}

        <Link href={`/content-hub/${draft.id}`} className="block hover:opacity-80 transition-opacity flex-1">
          <h3 className="font-medium text-sm line-clamp-2">{draft.title || 'Untitled'}</h3>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
            {draft.body?.slice(0, 200) || ''}
          </p>
        </Link>

        {godResult?.verdict && (
          <div className="text-xs">
            <span className="text-muted-foreground">GOD Review:</span>{' '}
            <span className={godResult.verdict === 'pass' ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
              {godResult.verdict.toUpperCase()}
            </span>
            {godResult.advocate_score != null && (
              <span className="text-muted-foreground"> · {godResult.advocate_score}/10</span>
            )}
          </div>
        )}

        {/* Action bar — always visible, primary action emphasized */}
        <div className="flex items-center gap-1.5 pt-2 border-t flex-wrap">
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
              className="bg-green-600 hover:bg-green-700 text-white"
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
              className="ml-auto text-muted-foreground hover:text-destructive"
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
