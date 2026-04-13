'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/kpi-card'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const LEGEND = [
  { label: 'Newsletter', color: 'bg-staging-bg' },
  { label: 'Social', color: 'bg-brand-primary' },
  { label: 'Blog/Video', color: 'bg-purple-500' },
  { label: 'Sponsorship', color: 'bg-brand-accent' },
]

function getDaysInMonth(year: number, month: number) {
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const offset = firstDay === 0 ? 6 : firstDay - 1
  return { daysInMonth, offset }
}

export default function CalendarioPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())

  const { daysInMonth, offset } = getDaysInMonth(year, month)
  const monthName = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const prev = () => { if (month === 0) { setMonth(11); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const next = () => { if (month === 11) { setMonth(0); setYear(y => y + 1) } else setMonth(m => m + 1) }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Editorial Calendar</h1>
        <Button className="bg-staging-bg hover:bg-staging-bg/90 text-white">
          <Plus className="size-4" />
          Add
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={prev}><ChevronLeft className="size-4" /></Button>
        <span className="text-lg font-medium capitalize">{monthName}</span>
        <Button variant="ghost" size="icon" onClick={next}><ChevronRight className="size-4" /></Button>
      </div>

      <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
        {DAYS.map(d => (
          <div key={d} className="bg-secondary p-2 text-center text-xs font-medium text-muted-foreground">{d}</div>
        ))}
        {Array.from({ length: offset }).map((_, i) => (
          <div key={`empty-${i}`} className="bg-background p-2 min-h-[80px]" />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1
          const isToday = day === now.getDate() && month === now.getMonth() && year === now.getFullYear()
          return (
            <div key={day} className={`bg-background p-2 min-h-[80px] ${isToday ? 'ring-2 ring-brand-primary ring-inset' : ''}`}>
              <span className={`text-xs ${isToday ? 'font-bold text-brand-primary' : 'text-muted-foreground'}`}>{day}</span>
            </div>
          )
        })}
      </div>

      <div className="flex items-center gap-4">
        {LEGEND.map(l => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className={`size-3 rounded-sm ${l.color}`} />
            <span className="text-xs text-muted-foreground">{l.label}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <KPICard title="Scheduled" value={0} />
        <KPICard title="In production" value={0} />
        <KPICard title="Approved" value={0} />
      </div>
    </div>
  )
}
