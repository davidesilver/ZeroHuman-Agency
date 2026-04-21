'use client'

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
import { Check, Archive, X, ExternalLink } from 'lucide-react'

export interface ResearchItem {
  id: string
  title: string
  url: string
  source_name: string
  retriever_type: string
  status: string
  final_score: number | null
  summary: string
  created_at: string
  scores?: Array<{
    final_score: number
    applicability: number
    credibility: number
    alignment: number
    reasoning: string
  }>
}

interface ItemsTableProps {
  items: ResearchItem[]
  onAction: (id: string, action: string) => void
  isLoading?: boolean
}

function scoreColor(score: number | null): string {
  if (score === null) return 'text-muted-foreground'
  if (score >= 8) return 'text-green-600'
  if (score >= 6) return 'text-brand-primary'
  if (score >= 4) return 'text-brand-accent'
  return 'text-red-500'
}

function statusBadgeVariant(status: string) {
  switch (status) {
    case 'approved': return 'default' as const
    case 'scored': return 'secondary' as const
    case 'rejected': return 'destructive' as const
    case 'archived': return 'secondary' as const
    default: return 'outline' as const
  }
}

function retrieverLabel(retriever_type: string): string {
  const map: Record<string, string> = {
    semantic: 'SEMANTIC',
    practitioner: 'PRACTITIONER',
    trusted_source: 'RSS',
    keyword: 'KEYWORD',
    trend: 'TREND',
    manual: 'MANUAL',
  }
  return map[retriever_type] || retriever_type.toUpperCase()
}

export function ItemsTable({ items, onAction, isLoading }: ItemsTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        Loading...
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        No items found. Run a search to get started.
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-24">Retriever</TableHead>
          <TableHead className="w-20">Status</TableHead>
          <TableHead className="w-24">Source</TableHead>
          <TableHead>Title</TableHead>
          <TableHead className="w-16 text-right">Score</TableHead>
          <TableHead className="w-40 text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => {
          const score = item.final_score ?? item.scores?.[0]?.final_score ?? null
          return (
            <TableRow key={item.id}>
              <TableCell>
                <Badge variant="secondary" className="text-[10px]">
                  {retrieverLabel(item.retriever_type)}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={statusBadgeVariant(item.status)} className="text-[10px]">
                  {item.status.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground truncate max-w-[100px]">
                {item.source_name}
              </TableCell>
              <TableCell>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm hover:text-brand-primary transition-colors flex items-center gap-1"
                >
                  <span className="line-clamp-1">{item.title}</span>
                  <ExternalLink className="size-3 shrink-0 text-muted-foreground" />
                </a>
                {item.summary && (
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{item.summary}</p>
                )}
              </TableCell>
              <TableCell className="text-right">
                <span className={`text-sm font-bold ${scoreColor(score)}`}>
                  {score !== null ? score.toFixed(1) : '—'}
                </span>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center gap-1 justify-end">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => onAction(item.id, 'approved')}
                    title="Approve"
                  >
                    <Check className="size-3 text-green-600" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => onAction(item.id, 'archived')}
                    title="Archive"
                  >
                    <Archive className="size-3 text-muted-foreground" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => onAction(item.id, 'rejected')}
                    title="Reject"
                  >
                    <X className="size-3 text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
