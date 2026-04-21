'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { KPICard } from '@/components/dashboard/kpi-card'
import { ChevronLeft, ChevronRight, Plus, Loader2 } from 'lucide-react'

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
  // YYYY-MM-DD (from calendar_events.scheduled_date DATE column, or date portion
  // extracted from content_drafts.scheduled_at timestamptz).
  scheduled_date: string
  scheduled_time?: string | null
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
  const [dialogOpen, setDialogOpen] = useState(false)
  const [formTitle, setFormTitle] = useState('')
  const [formType, setFormType] = useState('social')
  const [formDate, setFormDate] = useState('')
  const [formTime, setFormTime] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const { daysInMonth, offset } = getDaysInMonth(year, month)
  const monthName = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const fetchEvents = useCallback(async () => {
    try {
      const resp = await fetch(`/api/calendar/events?year=${year}&month=${month}`)
      const json = await resp.json()
      if (json.success) {
        const calEvents = (json.data.events || []) as CalendarEvent[]
        // Also merge scheduled drafts as events
        type ScheduledDraft = {
          id: string
          title?: string
          content_type?: string
          platform?: string
          scheduled_at: string
          status: string
        }
        const drafts: CalendarEvent[] = (json.data.scheduled_drafts || []).map((d: ScheduledDraft) => {
          // content_drafts.scheduled_at is timestamptz — split into date + time to
          // align with calendar_events shape. Use ISO parse then local-date parts
          // so the day lands on the user's wall clock, not UTC.
          const ts = new Date(d.scheduled_at)
          const pad = (n: number) => String(n).padStart(2, '0')
          const scheduled_date = `${ts.getFullYear()}-${pad(ts.getMonth() + 1)}-${pad(ts.getDate())}`
          const scheduled_time = `${pad(ts.getHours())}:${pad(ts.getMinutes())}`
          return {
            id: d.id,
            title: d.title || 'Scheduled post',
            event_type: d.content_type || d.platform || 'post',
            scheduled_date,
            scheduled_time,
            status: d.status,
          }
        })
        // Merge, dedup by id
        const seen = new Set(calEvents.map(e => e.id))
        const merged = [...calEvents, ...drafts.filter((d) => !seen.has(d.id))]
        setEvents(merged)
      }
    } catch {}
  }, [year, month])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  const prev = () => { if (month === 0) { setMonth(11); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const next = () => { if (month === 11) { setMonth(0); setYear(y => y + 1) } else setMonth(m => m + 1) }

  const openDialog = () => {
    setFormTitle('')
    setFormType('social')
    setFormDate(new Date(year, month, now.getDate()).toISOString().split('T')[0])
    setFormTime('')
    setSaveError(null)
    setDialogOpen(true)
  }

  const handleSaveEvent = async () => {
    if (!formTitle.trim() || !formDate) return
    setSaving(true)
    setSaveError(null)
    try {
      const resp = await fetch('/api/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formTitle.trim(),
          event_type: formType,
          scheduled_date: formDate,
          scheduled_time: formTime || undefined,
        }),
      })
      const json = await resp.json()
      if (json.success) {
        setDialogOpen(false)
        fetchEvents()
      } else {
        setSaveError(json.error?.message || 'Failed to create event')
      }
    } catch {
      setSaveError('Network error')
    }
    setSaving(false)
  }

  // Group events by day. scheduled_date is a YYYY-MM-DD string; parse the day
  // part directly to avoid timezone shifts that `new Date('YYYY-MM-DD')` can
  // introduce (it would be interpreted as UTC midnight).
  const eventsByDay: Record<number, CalendarEvent[]> = {}
  for (const event of events) {
    if (!event.scheduled_date) continue
    const parts = event.scheduled_date.split('-')
    const day = parseInt(parts[2], 10)
    if (!Number.isFinite(day)) continue
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
        <Button className="bg-staging-bg hover:bg-staging-bg/90 text-white" onClick={openDialog}>
          <Plus className="size-4" />
          Add
        </Button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Calendar Event</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="event-title">Title</Label>
              <Input
                id="event-title"
                value={formTitle}
                onChange={e => setFormTitle(e.target.value)}
                placeholder="Newsletter #42, LinkedIn post..."
              />
            </div>
            <div className="space-y-1.5">
              <Label>Type</Label>
              <Select value={formType} onValueChange={(v) => { if (v) setFormType(v) }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newsletter">Newsletter</SelectItem>
                  <SelectItem value="social">Social</SelectItem>
                  <SelectItem value="blog_video">Blog / Video</SelectItem>
                  <SelectItem value="sponsorship">Sponsorship</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="event-date">Date</Label>
                <Input
                  id="event-date"
                  type="date"
                  value={formDate}
                  onChange={e => setFormDate(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="event-time">Time <span className="text-muted-foreground text-xs">(optional)</span></Label>
                <Input
                  id="event-time"
                  type="time"
                  value={formTime}
                  onChange={e => setFormTime(e.target.value)}
                />
              </div>
            </div>
            {saveError && <p className="text-sm text-destructive">{saveError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSaveEvent}
              disabled={saving || !formTitle.trim() || !formDate}
              className="bg-staging-bg hover:bg-staging-bg/90 text-white"
            >
              {saving ? <Loader2 className="size-4 animate-spin" /> : null}
              {saving ? 'Saving...' : 'Add Event'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
