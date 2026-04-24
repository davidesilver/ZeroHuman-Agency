'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useBrand } from '@/lib/brand-context'

interface CostData {
  spend_today: number
  daily_budget: number | null  // global env cap (null = unlimited)
  brand_budget: number | null // per-brand DB cap (null = unlimited)
}

export function APISpendRow() {
  const { activeBrand } = useBrand()
  const [costs, setCosts] = useState<CostData | null>(null)

  useEffect(() => {
    fetch('/api/system/costs?period=today')
      .then(r => r.json())
      .then(j => { if (j.success) setCosts(j.data) })
      .catch(() => {})
  }, [activeBrand?.id])

  const effectiveBudget = costs
    ? (costs.brand_budget != null ? costs.brand_budget : costs.daily_budget)
    : null

  const spendText = costs
    ? `$${costs.spend_today.toFixed(2)}`
    : '…'

  const budgetText = effectiveBudget != null
    ? `limit $${effectiveBudget.toFixed(2)}`
    : 'unlimited'

  return (
    <div className="h-8 bg-brand-secondary/10 flex items-center justify-between px-4 rounded-md">
      <span className="text-sm text-muted-foreground">
        API spend today: {spendText} — {budgetText}
      </span>
      <Link
        href="/costi-api"
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        Details &rarr;
      </Link>
    </div>
  )
}