'use client'

import { cn } from '@/lib/utils'

interface StatusTabsProps {
  counts: {
    total: number
    new: number
    scored: number
    approved: number
    archived: number
    rejected: number
  }
  activeTab: string
  onTabChange: (tab: string) => void
}

const TABS = [
  { key: 'all', label: 'ALL', countKey: 'total' },
  { key: 'new', label: 'NEW', countKey: 'new' },
  { key: 'scored', label: 'SCORED', countKey: 'scored' },
  { key: 'approved', label: 'APPROVED', countKey: 'approved' },
  { key: 'archived', label: 'ARCHIVED', countKey: 'archived' },
  { key: 'rejected', label: 'REJECTED', countKey: 'rejected' },
] as const

export function StatusTabs({ counts, activeTab, onTabChange }: StatusTabsProps) {
  return (
    <div className="flex gap-1 border-b border-border">
      {TABS.map((tab) => {
        const count = counts[tab.countKey as keyof typeof counts] || 0
        const isActive = activeTab === tab.key
        return (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors border-b-2',
              isActive
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {count} {tab.label}
          </button>
        )
      })}
    </div>
  )
}
