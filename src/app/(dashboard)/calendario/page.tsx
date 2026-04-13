'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/kpi-card'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const LEGEND = [
  { label: 'Newsletter', color: 'bg-staging-bg', type: 'newsletter' },
  { label: 'Social', color: 'bg-brand-primary', type: 'post' },
  { label: 'Blog/Video', color: 'bg-purple-500', type: 'blog' },
  { label: 'Sponsorship', color: 'bg-brand-accent', type: 'sponsorship' },
]

interface CalendarEvent {
  id: string
  title: string
  event_type: string
  scheduled_at: string
  status: string
}

function getDaysInMonth(year: number, month: number) {
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const offset = firstDay === 0 ? 6 : firstDay - 1
  return { daysInMonth, offset }
}

function getEventColor(type: string): string {
  const map: Record<string, string> = {
    newsletter: 'bg-staging-bg',
    email: 'bg-staging-bg',
    post: 'bg-brand-primary',
    linkedin: 'bg-brand-primary',
    social: 'bg-brand-primary',
    blog: 'bg-purple-500',
    video: 'bg-purple-500',
    sponsorship: 'bg-brand-accent',
  }
  return map[type] || 'bg-brand-primary'
}

export default function CalendarioPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const { daysInMonth, offset } = getDaysInMonth(year, month)
  const monthName = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const fetchEvents = useCallback(async () => {
    setIsLoading(true)
    try {
      const resp = await fetch(`/api/calendar/events?year=${year}&month=${month}`)
      const json = await resp.json()
      if (json.success) {
        const calEvents = (json.data.events || []) as CalendarEvent[]
        // Also merge scheduled drafts as events
        const drafts = (json.data.scheduled_drafts || []).map((d: any) => ({
          id: d.id,
          title: d.title || 'Scheduled post',
          event_type: d.content_type || d.platform || 'post',
          scheduled_at: d.scheduled_at,
          status: d.status,
        }))
        // Merge, dedup by id
        const seen = new Set(calEvents.map(e => e.id))
        const merged = [...calEvents, ...drafts.filter((d: CalendarEvent) => !seen.has(d.id))]
        setEvents(merged)
      }
    } catch {}
    setIsLoading(false)
  }, [year, month])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  const prev = () => { if (month === 0) { setMonth(11); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const next = () => { if (month === 11) { setMonth(0); setYear(y => y + 1) } else setMonth(m => m + 1) }

  // Group events by day
  const eventsByDay: Record<number, CalendarEvent[]> = {}
  for (const event of events) {
    const d = new Date(event.scheduled_at)
    const day = d.getDate()
    if (!eventsByDay[day]) eventsByDay[day] = []
    eventsByDay[day].push(event)
  }

  const scheduledCount = events.filter(e => e.status === 'scheduled').length
  const approvedCount = events.filter(e => e.status === 'approved').length
  const inProductionCount = events.filter(e => ['draft', 'in_review', 'god_mode'].includes(e.status)).length

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
          const dayEvents = eventsByDay[day] || []
          return (
            <div key={day} className={`bg-background p-2 min-h-[80px] ${isToday ? 'ring-2 ring-brand-primary ring-inset' : ''}`}>
              <span className={`text-xs ${isToday ? 'font-bold text-brand-primary' : 'text-muted-foreground'}`}>{day}</span>
              <div className="mt-1 space-y-0.5">
                {dayEvents.slice(0, 3).map(event => (
                  <div
                    key={event.id}
                    className={`${getEventColor(event.event_type)} rounded px-1 py-0.5 text-white text-[9px] truncate`}
                    title={event.title}
                  >
                    {event.title}
                  </div>
                ))}
                {dayEvents.length > 3 && (
                  <span className="text-[9px] text-muted-foreground">+{dayEvents.length - 3} more</span>
                )}
              </div>
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
        <KPICard title="Scheduled" value={scheduledCount} />
        <KPICard title="In production" value={inProductionCount} />
        <KPICard title="Approved" value={approvedCount} />
      </div>
    </div>
  )
}
