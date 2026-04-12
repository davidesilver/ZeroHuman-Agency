'use client'

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { DraftCard } from '@/components/content/draft-card'

const STATUS_TABS = [
  { key: 'all', label: 'TUTTI' },
  { key: 'draft', label: 'BOZZE' },
  { key: 'in_review', label: 'IN REVIEW' },
  { key: 'god_mode', label: 'GOD MODE' },
  { key: 'approved', label: 'APPROVATI' },
  { key: 'scheduled', label: 'SCHEDULATI' },
  { key: 'published', label: 'PUBBLICATI' },
  { key: 'archived', label: 'ARCHIVIATI' },
] as const

export default function ContentHubPage() {
  const [drafts, setDrafts] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState('all')
  const [isLoading, setIsLoading] = useState(true)

  const fetchDrafts = useCallback(async () => {
    setIsLoading(true)
    const params = new URLSearchParams({ per_page: '50' })
    if (activeTab !== 'all') params.set('status', activeTab)
    try {
      const resp = await fetch(`/api/content/drafts?${params}`)
      const json = await resp.json()
      if (json.success) setDrafts(json.data.drafts || [])
    } catch {}
    setIsLoading(false)
  }, [activeTab])

  useEffect(() => { fetchDrafts() }, [fetchDrafts])

  const handleAction = async (id: string, action: string) => {
    if (action === 'god_mode') {
      await fetch(`/api/content/drafts/${id}/god-mode`, { method: 'POST' })
    } else {
      await fetch(`/api/content/drafts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: action }),
      })
    }
    fetchDrafts()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Content Hub</h1>

      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors border-b-2',
              activeTab === tab.key
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Caricamento...</div>
      ) : drafts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Nessun contenuto. Genera contenuti dalla pagina Ricerca.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} onAction={handleAction} />
          ))}
        </div>
      )}
    </div>
  )
}
