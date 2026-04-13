'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Settings as SettingsIcon, Key, Bot, Mail, Share2, Database, Clock } from 'lucide-react'

const CONFIG_SECTIONS = [
  {
    title: 'API Keys',
    icon: Key,
    items: [
      { key: 'ANTHROPIC_API_KEY', label: 'Claude API', status: 'check' },
      { key: 'OPENROUTER_API_KEY', label: 'OpenRouter', status: 'check' },
      { key: 'SERPER_API_KEY', label: 'Serper (search)', status: 'check' },
      { key: 'YOUTUBE_API_KEY', label: 'YouTube Data', status: 'check' },
      { key: 'RESEND_API_KEY', label: 'Resend (email)', status: 'check' },
    ],
  },
  {
    title: 'LLM Configuration',
    icon: Bot,
    items: [
      { key: 'scoring_model', label: 'Scoring Model', value: 'claude-sonnet-4-20250514' },
      { key: 'auto_approve', label: 'Auto-approve threshold', value: '≥ 8.0' },
      { key: 'auto_reject', label: 'Auto-reject threshold', value: '≤ 3.0' },
    ],
  },
  {
    title: 'Email / Newsletter',
    icon: Mail,
    items: [
      { key: 'from_email', label: 'From email', value: 'newsletter@yourdomain.com' },
      { key: 'from_name', label: 'From name', value: 'Content Engine' },
    ],
  },
  {
    title: 'Social Platforms',
    icon: Share2,
    items: [
      { key: 'linkedin', label: 'LinkedIn', status: 'configured' },
      { key: 'twitter', label: 'Twitter/X', status: 'not_configured' },
      { key: 'instagram', label: 'Instagram', status: 'not_configured' },
      { key: 'tiktok', label: 'TikTok', status: 'not_configured' },
    ],
  },
  {
    title: 'Research Pipeline',
    icon: Database,
    items: [
      { key: 'dedup_threshold', label: 'Dedup similarity threshold', value: '0.85' },
      { key: 'max_items', label: 'Max items per retriever', value: '100' },
    ],
  },
  {
    title: 'Scheduler',
    icon: Clock,
    items: [
      { key: 'daily_pipeline', label: 'Daily research pipeline', value: '07:00 CET' },
      { key: 'feedback_loop', label: 'Feedback loop update', value: '02:00 CET' },
      { key: 'publish_scheduled', label: 'Publish scheduled posts', value: 'every 10min' },
    ],
  },
]

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Badge variant="outline" className="text-xs">
          <SettingsIcon className="size-3 mr-1" />
          Read-only (edit .env.local)
        </Badge>
      </div>

      <div className="grid gap-4">
        {CONFIG_SECTIONS.map(section => (
          <Card key={section.title}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <section.icon className="size-4 text-muted-foreground" />
                {section.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {section.items.map(item => (
                  <div key={item.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{item.label}</span>
                      <code className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">{item.key}</code>
                    </div>
                    <div>
                      {'status' in item && item.status === 'check' && (
                        <Badge variant="outline" className="text-[10px] text-amber-600">Check .env.local</Badge>
                      )}
                      {'status' in item && item.status === 'configured' && (
                        <Badge className="text-[10px] bg-green-600">Configured</Badge>
                      )}
                      {'status' in item && item.status === 'not_configured' && (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground">Not configured</Badge>
                      )}
                      {'value' in item && (
                        <span className="text-sm font-mono text-muted-foreground">{item.value}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
