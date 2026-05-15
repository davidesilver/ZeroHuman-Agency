'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Loader2, Upload, Users, List, CheckCircle2, AlertCircle, Key } from 'lucide-react'
import { useBrand } from '@/lib/brand-context'

// ── Types ────────────────────────────────────────────────────────────────────

interface BrevoList {
  id: number
  name: string
  total_subscribers: number
}

interface SyncResult {
  synced: number
  errors: Array<{ email: string; reason: string }>
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AudiencePage() {
  const { activeBrand } = useBrand()
  const brandId = activeBrand?.id
  const [apiKey, setApiKey] = useState('')
  const [savingKey, setSavingKey] = useState(false)
  const [keySaved, setKeySaved] = useState(false)

  const [lists, setLists] = useState<BrevoList[]>([])
  const [loadingLists, setLoadingLists] = useState(false)

  const [selectedListId, setSelectedListId] = useState<number | null>(null)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  const fileRef = useRef<HTMLInputElement>(null)

  // Load lists once API key is saved
  const loadLists = useCallback(async () => {
    setLoadingLists(true)
    try {
      const res = await fetch('/api/email-marketing/lists')
      if (!res.ok) throw new Error(await res.text())
      setLists(await res.json())
    } catch (err) {
      // Key not yet configured — silently swallow
    } finally {
      setLoadingLists(false)
    }
  }, [])

  useEffect(() => {
    if (brandId) loadLists()
  }, [brandId, loadLists])

  async function saveApiKey() {
    if (!apiKey.trim()) return
    setSavingKey(true)
    try {
      await fetch('/api/internal/brand-secrets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'brevo', key_name: 'api_key', value: apiKey.trim() }),
      })
      setKeySaved(true)
      setApiKey('')
      await loadLists()
    } catch {
      // ignore
    } finally {
      setSavingKey(false)
    }
  }

  async function uploadCSV() {
    if (!csvFile) return
    setSyncing(true)
    setSyncResult(null)
    setSyncError(null)
    try {
      const text = await csvFile.text()
      const url = selectedListId
        ? `/api/email-marketing/contacts?list_id=${selectedListId}`
        : '/api/email-marketing/contacts'
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'text/csv' },
        body: text,
      })
      if (!res.ok) {
        setSyncError(await res.text())
        return
      }
      setSyncResult(await res.json())
      setCsvFile(null)
      if (fileRef.current) fileRef.current.value = ''
      await loadLists()
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Audience</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Connect Brevo for email marketing, contact management, and automations.
        </p>
      </div>

      {/* API Key */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key className="h-4 w-4" />
            Brevo API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {keySaved && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <CheckCircle2 className="h-4 w-4" />
              Key saved. Existing key is hidden for security.
            </div>
          )}
          <div className="flex gap-2">
            <Input
              type="password"
              placeholder="xkeysib-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && saveApiKey()}
              className="font-mono text-sm"
            />
            <Button onClick={saveApiKey} disabled={savingKey || !apiKey.trim()}>
              {savingKey ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Get your API key from Brevo → Settings → SMTP &amp; API → API Keys.
            Stored encrypted per-brand.
          </p>
        </CardContent>
      </Card>

      {/* Contact Lists */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <List className="h-4 w-4" />
            Contact Lists
            {loadingLists && <Loader2 className="h-3 w-3 animate-spin ml-1" />}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {lists.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {loadingLists ? 'Loading...' : 'No lists found. Add your Brevo API key above.'}
            </p>
          ) : (
            <div className="space-y-2">
              {lists.map((lst) => (
                <div
                  key={lst.id}
                  onClick={() => setSelectedListId(lst.id === selectedListId ? null : lst.id)}
                  className={`flex items-center justify-between rounded-md border p-3 cursor-pointer transition-colors ${
                    selectedListId === lst.id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{lst.name}</span>
                  </div>
                  <Badge variant="secondary">{lst.total_subscribers} contacts</Badge>
                </div>
              ))}
            </div>
          )}
          {selectedListId && (
            <p className="text-xs text-muted-foreground mt-2">
              New contacts from CSV will be added to the selected list.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Upload CSV */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4" />
            Import Contacts (CSV)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-sm">CSV file</Label>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              className="mt-1 block text-sm"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Required column: <code className="font-mono">email</code>. Optional:{' '}
              <code className="font-mono">first_name</code>,{' '}
              <code className="font-mono">last_name</code>. Extra columns become Brevo attributes.
            </p>
          </div>

          <Button
            onClick={uploadCSV}
            disabled={!csvFile || syncing || lists.length === 0}
            className="w-full"
          >
            {syncing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Syncing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload &amp; Sync to Brevo
              </>
            )}
          </Button>

          {syncResult && (
            <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              <div className="flex items-center gap-2 font-medium">
                <CheckCircle2 className="h-4 w-4" />
                {syncResult.synced} contacts synced
              </div>
              {syncResult.errors.length > 0 && (
                <div className="mt-2 space-y-1">
                  {syncResult.errors.map((e) => (
                    <div key={e.email} className="text-xs text-red-600">
                      {e.email}: {e.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {syncError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              {syncError}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
