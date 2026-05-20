'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Loader2, Mail, Zap } from 'lucide-react'

interface AutomationStep {
  step: number
  delay_days: number
  subject: string
  html_content: string
}

interface Automation {
  id: string
  name: string
  template_key: 'welcome' | 'nurture' | 'win-back'
  status: 'active' | 'inactive'
  steps: AutomationStep[]
  created_at: string
}

const TEMPLATES = [
  { key: 'welcome',  label: 'Welcome series',  description: '3-step onboarding sequence for new subscribers.' },
  { key: 'nurture',  label: 'Nurture series',  description: '5-step value-driven sequence to engage subscribers.' },
  { key: 'win-back', label: 'Win-back series', description: '2-step re-engagement for inactive subscribers.' },
] as const

export default function AutomationsPage() {
  const [automations, setAutomations] = useState<Automation[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<Record<string, boolean>>({})
  const [creating, setCreating] = useState<Record<string, boolean>>({})

  async function load() {
    const res = await fetch('/api/email-marketing/automations')
    if (res.ok) setAutomations(await res.json())
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function create(templateKey: string) {
    setCreating(c => ({ ...c, [templateKey]: true }))
    try {
      const res = await fetch('/api/email-marketing/automations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_key: templateKey }),
      })
      if (res.ok) await load()
    } finally {
      setCreating(c => ({ ...c, [templateKey]: false }))
    }
  }

  async function toggle(automation: Automation) {
    setToggling(t => ({ ...t, [automation.id]: true }))
    try {
      const res = await fetch(`/api/email-marketing/automations/${automation.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: automation.status === 'active' ? 'inactive' : 'active' }),
      })
      if (res.ok) {
        setAutomations(list =>
          list.map(a =>
            a.id === automation.id
              ? { ...a, status: a.status === 'active' ? 'inactive' : 'active' }
              : a
          )
        )
      }
    } finally {
      setToggling(t => ({ ...t, [automation.id]: false }))
    }
  }

  const existingKeys = new Set(automations.map(a => a.template_key))

  return (
    <div className="space-y-6 p-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold">Email Automations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Multi-step Brevo automations. Activate to map them to your Brevo account.
        </p>
      </div>

      {/* Create templates */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Available templates</h2>
        {TEMPLATES.map(t => {
          const existing = automations.find(a => a.template_key === t.key)
          return (
            <Card key={t.key}>
              <div className="flex items-center gap-4 p-4">
                <Zap className="h-5 w-5 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{t.label}</p>
                  <p className="text-xs text-muted-foreground">{t.description}</p>
                </div>
                {existing ? (
                  <Badge variant={existing.status === 'active' ? 'default' : 'secondary'}>
                    {existing.status}
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => create(t.key)}
                    disabled={creating[t.key]}
                  >
                    {creating[t.key] ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                    Add
                  </Button>
                )}
              </div>
            </Card>
          )
        })}
      </div>

      {/* Active automations */}
      {automations.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Your automations</h2>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : (
            automations.map(auto => (
              <Card key={auto.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Mail className="h-4 w-4" /> {auto.name}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant={auto.status === 'active' ? 'default' : 'secondary'}>
                        {auto.status}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggle(auto)}
                        disabled={toggling[auto.id]}
                      >
                        {toggling[auto.id]
                          ? <Loader2 className="h-3 w-3 animate-spin" />
                          : auto.status === 'active' ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {auto.steps.map(step => (
                      <div key={step.step} className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="w-6 h-6 rounded-full border flex items-center justify-center text-[11px] font-medium">
                          {step.step}
                        </span>
                        <span className="text-muted-foreground w-20 shrink-0">
                          Day {step.delay_days}
                        </span>
                        <span className="truncate">{step.subject}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  )
}
