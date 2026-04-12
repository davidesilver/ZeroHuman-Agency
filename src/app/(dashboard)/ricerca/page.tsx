'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { StatusTabs } from '@/components/research/status-tabs'
import { VolumeReport } from '@/components/research/volume-report'
import { ItemsTable } from '@/components/research/items-table'
import { Search, Loader2 } from 'lucide-react'

interface Counts {
  total: number
  new: number
  scored: number
  approved: number
  archived: number
  rejected: number
}

const RETRIEVER_COLORS: Record<string, string> = {
  semantic: '#3B82F6',
  practitioner: '#8B5CF6',
  trusted_source: '#10B981',
  keyword: '#F59E0B',
  trend: '#EF4444',
}

export default function RicercaPage() {
  const [items, setItems] = useState<any[]>([])
  const [counts, setCounts] = useState<Counts>({ total: 0, new: 0, scored: 0, approved: 0, archived: 0, rejected: 0 })
  const [activeTab, setActiveTab] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [isTriggering, setIsTriggering] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchStats = useCallback(async () => {
    try {
      const resp = await fetch('/api/research/stats')
      const json = await resp.json()
      if (json.success) setCounts(json.data)
    } catch {}
  }, [])

  const fetchItems = useCallback(async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: '30',
        sort_by: 'created_at',
        sort_order: 'desc',
      })
      if (activeTab !== 'all') params.set('status', activeTab)

      const resp = await fetch(`/api/research/items?${params}`)
      const json = await resp.json()
      if (json.success) {
        setItems(json.data.items || [])
        setTotalPages(json.data.meta?.total_pages || 1)
      }
    } catch {}
    setIsLoading(false)
  }, [activeTab, page])

  useEffect(() => {
    fetchStats()
    fetchItems()
  }, [fetchStats, fetchItems])

  const handleAction = async (id: string, status: string) => {
    try {
      await fetch(`/api/research/items/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      fetchItems()
      fetchStats()
    } catch {}
  }

  const handleTrigger = async () => {
    setIsTriggering(true)
    try {
      await fetch('/api/research/trigger', { method: 'POST' })
      // Poll for completion
      setTimeout(() => {
        fetchItems()
        fetchStats()
        setIsTriggering(false)
      }, 3000)
    } catch {
      setIsTriggering(false)
    }
  }

  // Compute volume stats from items
  const retrieverCounts = items.reduce<Record<string, number>>((acc, item) => {
    acc[item.retriever_type] = (acc[item.retriever_type] || 0) + 1
    return acc
  }, {})

  const volumeStats = Object.entries(retrieverCounts).map(([name, count]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    count,
    color: RETRIEVER_COLORS[name] || '#6B7280',
  }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Ricerca</h1>
        <Button
          onClick={handleTrigger}
          disabled={isTriggering}
          className="bg-staging-bg hover:bg-staging-bg/90 text-white"
        >
          {isTriggering ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Ricerca in corso...
            </>
          ) : (
            <>
              <Search className="size-4" />
              Lancia Ricerca
            </>
          )}
        </Button>
      </div>

      <StatusTabs counts={counts} activeTab={activeTab} onTabChange={(tab) => { setActiveTab(tab); setPage(1) }} />

      {volumeStats.length > 0 && (
        <VolumeReport total={counts.total} stats={volumeStats} />
      )}

      <ItemsTable items={items} onAction={handleAction} isLoading={isLoading} />

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Precedente
          </Button>
          <span className="text-sm text-muted-foreground">
            Pagina {page} di {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Successiva
          </Button>
        </div>
      )}
    </div>
  )
}
