'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Check, Sparkles, Archive } from 'lucide-react'

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
  }
  onAction: (id: string, action: string) => void
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

export function DraftCard({ draft, onAction }: DraftCardProps) {
  const godResult = draft.god_mode_result as { verdict?: string; advocate_score?: number } | null

  return (
    <Card className="group">
      <CardContent className="pt-4 space-y-3">
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

        <div>
          <h3 className="font-medium text-sm line-clamp-2">{draft.title || 'Senza titolo'}</h3>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
            {draft.body?.slice(0, 200) || ''}
          </p>
        </div>

        {godResult?.verdict && (
          <div className="text-xs text-muted-foreground">
            GOD: <span className={godResult.verdict === 'pass' ? 'text-green-600' : 'text-amber-600'}>
              {godResult.verdict.toUpperCase()}
            </span>
            {godResult.advocate_score != null && ` (${godResult.advocate_score}/10)`}
          </div>
        )}

        <div className="flex items-center gap-1 pt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="ghost" size="xs" onClick={() => onAction(draft.id, 'approved')} title="Approva">
            <Check className="size-3 text-green-600" />
            Approva
          </Button>
          <Button variant="ghost" size="xs" onClick={() => onAction(draft.id, 'god_mode')} title="GOD Mode">
            <Sparkles className="size-3 text-brand-accent" />
            GOD
          </Button>
          <Button variant="ghost" size="xs" onClick={() => onAction(draft.id, 'archived')} title="Archivia">
            <Archive className="size-3 text-muted-foreground" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
