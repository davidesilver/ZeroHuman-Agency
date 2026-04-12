'use client'

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const TABS = [
  { key: 'all', label: 'TUTTI' },
  { key: 'draft', label: 'BOZZE' },
  { key: 'scheduled', label: 'PROGRAMMATI' },
  { key: 'published', label: 'PUBBLICATI' },
] as const

export default function BlogPage() {
  const [activeTab, setActiveTab] = useState('all')
  const [posts, setPosts] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchPosts = useCallback(async () => {
    setIsLoading(true)
    const params = new URLSearchParams({ content_type: 'blog', per_page: '50' })
    if (activeTab !== 'all') params.set('status', activeTab)
    try {
      const resp = await fetch(`/api/content/drafts?${params}`)
      const json = await resp.json()
      if (json.success) setPosts(json.data.drafts || [])
    } catch {}
    setIsLoading(false)
  }, [activeTab])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Blog Manager</h1>

      <div className="flex gap-1 border-b border-border">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.key
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="Pubblicati" value={posts.filter(p => p.status === 'published').length} />
        <KPICard title="In bozza" value={posts.filter(p => p.status === 'draft').length} />
        <KPICard title="Programmati" value={posts.filter(p => p.status === 'scheduled').length} />
        <KPICard title="Visite totali" value="—" subtitle="Collegare analytics" />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Caricamento...</div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Nessun articolo blog. Genera contenuti di tipo &quot;blog&quot; dal Content Hub.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Titolo</TableHead>
              <TableHead className="w-28">Data</TableHead>
              <TableHead className="w-20">Status</TableHead>
              <TableHead className="w-20 text-right">SEO</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {posts.map(post => (
              <TableRow key={post.id}>
                <TableCell className="font-medium">{post.title || 'Senza titolo'}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {post.created_at ? new Date(post.created_at).toLocaleDateString('it-IT') : '—'}
                </TableCell>
                <TableCell>
                  <Badge variant={post.status === 'published' ? 'default' : 'outline'} className="text-[10px]">
                    {post.status.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {post.seo_score ? `${post.seo_score}/100` : '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
