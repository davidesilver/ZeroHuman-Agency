'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Plus } from 'lucide-react'

export default function NewsletterPage() {
  const [newsletters, setNewsletters] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchNewsletters = useCallback(async () => {
    setIsLoading(true)
    try {
      const resp = await fetch('/api/newsletter?per_page=50')
      const json = await resp.json()
      if (json.success) setNewsletters(json.data.newsletters || [])
    } catch {}
    setIsLoading(false)
  }, [])

  useEffect(() => { fetchNewsletters() }, [fetchNewsletters])

  const statusVariant = (status: string) => {
    switch (status) {
      case 'sent': return 'default' as const
      case 'approved': return 'default' as const
      case 'scheduled': return 'secondary' as const
      default: return 'outline' as const
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Newsletter</h1>
        <Button className="bg-staging-bg hover:bg-staging-bg/90 text-white">
          <Plus className="size-4" />
          Genera Newsletter
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="Inviate questo mese" value={newsletters.filter(n => n.status === 'sent').length} />
        <KPICard title="Open rate medio" value="—" subtitle="Dati in arrivo" />
        <KPICard title="Iscritti" value="—" subtitle="Collegare ESP" />
        <KPICard title="CTR medio" value="—" subtitle="Dati in arrivo" />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Caricamento...</div>
      ) : newsletters.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Nessuna newsletter. Clicca &quot;Genera Newsletter&quot; per iniziare.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">#</TableHead>
              <TableHead>Titolo</TableHead>
              <TableHead className="w-28">Data</TableHead>
              <TableHead className="w-24">Open Rate</TableHead>
              <TableHead className="w-20">CTR</TableHead>
              <TableHead className="w-24">Stato</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {newsletters.map((nl) => (
              <TableRow key={nl.id}>
                <TableCell className="font-medium">{nl.edition_number}</TableCell>
                <TableCell>{nl.title}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {nl.sent_at ? new Date(nl.sent_at).toLocaleDateString('it-IT') : '—'}
                </TableCell>
                <TableCell>{nl.open_rate ? `${(nl.open_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>{nl.click_rate ? `${(nl.click_rate * 100).toFixed(1)}%` : '—'}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(nl.status)} className="text-[10px]">
                    {nl.status.toUpperCase()}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
