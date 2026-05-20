'use client'

import { useState } from 'react'

// ── Verified Knot mark (inline SVG, no external deps) ─────────────────────────
function ZHMark({ size = 56 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="ZeroHuman mark"
    >
      {/* Simplified Verified Knot — two interlocking masses with central void */}
      <rect x="8" y="8" width="36" height="84" rx="6" fill="#f5f0e8" />
      <rect x="56" y="8" width="36" height="84" rx="6" fill="#f5f0e8" />
      <rect x="8" y="40" width="84" height="20" rx="6" fill="#f5f0e8" />
      <rect x="36" y="36" width="28" height="28" rx="4" fill="#0f0f0f" />
      {/* Coral verification dot */}
      <circle cx="50" cy="50" r="5" fill="#FF6B6B" />
    </svg>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      onClick={copy}
      className="ml-2 px-2 py-0.5 text-xs rounded border border-[#3a3a3a] text-[#888] hover:text-[#f5f0e8] hover:border-[#f5f0e8] transition-colors"
    >
      {copied ? '✓ copied' : 'copy'}
    </button>
  )
}

// ── Status badge ──────────────────────────────────────────────────────────────
type Status = 'idle' | 'loading' | 'ok' | 'error'

// ── Manual credentials form ───────────────────────────────────────────────────
function ManualForm() {
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState('')
  const [anon, setAnon] = useState('')
  const [service, setService] = useState('')
  const [testStatus, setTestStatus] = useState<Status>('idle')
  const [testMsg, setTestMsg] = useState('')
  const [saveStatus, setSaveStatus] = useState<Status>('idle')
  const [saveMsg, setSaveMsg] = useState('')

  async function testConnection() {
    setTestStatus('loading')
    setTestMsg('')
    try {
      const res = await fetch('/api/bootstrap/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ supabase_url: url, supabase_anon_key: anon, supabase_service_key: service }),
      })
      const json = await res.json()
      if (json.success) {
        setTestStatus('ok')
        setTestMsg(json.message || 'Connection successful')
      } else {
        setTestStatus('error')
        setTestMsg(json.error || 'Connection failed')
      }
    } catch {
      setTestStatus('error')
      setTestMsg('Network error')
    }
  }

  async function saveConfig() {
    setSaveStatus('loading')
    setSaveMsg('')
    try {
      const res = await fetch('/api/bootstrap/save-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ supabase_url: url, supabase_anon_key: anon, supabase_service_key: service }),
      })
      const json = await res.json()
      if (json.success) {
        setSaveStatus('ok')
        setSaveMsg('Saved! Restart the server to continue.')
      } else {
        setSaveStatus('error')
        setSaveMsg(json.error || 'Save failed')
      }
    } catch {
      setSaveStatus('error')
      setSaveMsg('Network error')
    }
  }

  const inputClass = "w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded-md px-3 py-2 text-sm font-mono text-[#f5f0e8] placeholder:text-[#555] focus:outline-none focus:border-[#555]"

  return (
    <div className="mt-4 border border-[#2a2a2a] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm text-[#888] hover:text-[#f5f0e8] transition-colors"
      >
        <span>Advanced: enter credentials manually</span>
        <span className="text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-[#2a2a2a]">
          <p className="text-xs text-[#666] pt-3">
            Find these in your{' '}
            <a href="https://supabase.com/dashboard/project/_/settings/api" target="_blank" rel="noopener noreferrer" className="underline hover:text-[#f5f0e8]">
              Supabase project settings
            </a>
            .
          </p>

          <div className="space-y-2">
            <label className="text-xs text-[#888]">Project URL</label>
            <input
              className={inputClass}
              placeholder="https://xxx.supabase.co"
              value={url}
              onChange={e => setUrl(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-[#888]">Anon / Public Key</label>
            <input
              className={inputClass}
              placeholder="eyJ..."
              value={anon}
              onChange={e => setAnon(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-[#888]">Service Role Key</label>
            <input
              className={inputClass}
              type="password"
              placeholder="eyJ..."
              value={service}
              onChange={e => setService(e.target.value)}
            />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={testConnection}
              disabled={!url || !anon || testStatus === 'loading'}
              className="px-3 py-1.5 text-sm rounded-md border border-[#3a3a3a] text-[#aaa] hover:text-[#f5f0e8] hover:border-[#666] disabled:opacity-40 transition-colors"
            >
              {testStatus === 'loading' ? 'Testing…' : 'Test connection'}
            </button>
            <button
              onClick={saveConfig}
              disabled={testStatus !== 'ok' || saveStatus === 'loading'}
              className="px-3 py-1.5 text-sm rounded-md bg-[#f5f0e8] text-[#0f0f0f] hover:bg-white disabled:opacity-40 transition-colors"
            >
              {saveStatus === 'loading' ? 'Saving…' : 'Save & continue'}
            </button>
          </div>

          {testStatus === 'ok' && (
            <p className="text-xs text-[#4ade80]">✓ {testMsg}</p>
          )}
          {testStatus === 'error' && (
            <p className="text-xs text-[#f87171]">✗ {testMsg}</p>
          )}
          {saveStatus === 'ok' && (
            <p className="text-xs text-[#4ade80]">✓ {saveMsg}</p>
          )}
          {saveStatus === 'error' && (
            <p className="text-xs text-[#f87171]">✗ {saveMsg}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function BootstrapPage() {
  const initCmd = 'npx @zerohuman/cli init'

  return (
    <div className="w-full max-w-md">
      {/* Logo */}
      <div className="flex flex-col items-center mb-10">
        <ZHMark size={56} />
        <h1 className="mt-4 text-xl font-semibold tracking-tight">ZeroHuman Agency</h1>
        <p className="mt-1 text-sm text-[#666]">AI content operations platform</p>
      </div>

      {/* Status card */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl p-6 space-y-5">
        <div>
          <h2 className="text-base font-medium text-[#f5f0e8]">Database not configured</h2>
          <p className="mt-1 text-sm text-[#777]">
            ZeroHuman needs a Supabase project to store brands, content, and configuration.
          </p>
        </div>

        {/* Option A: CLI */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-[#888] uppercase tracking-wide">Option A — CLI (recommended)</p>
          <p className="text-sm text-[#aaa]">
            Run the interactive setup wizard in your terminal:
          </p>
          <div className="flex items-center bg-[#111] border border-[#2a2a2a] rounded-md px-3 py-2.5">
            <code className="flex-1 text-sm font-mono text-[#f5f0e8]">{initCmd}</code>
            <CopyButton text={initCmd} />
          </div>
          <p className="text-xs text-[#555]">
            The CLI guides you through Supabase setup, LLM providers, and all integrations.
          </p>
        </div>

        <div className="border-t border-[#2a2a2a]" />

        {/* Option B: Manual */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-[#888] uppercase tracking-wide">Option B — Manual</p>
          <p className="text-sm text-[#aaa]">
            Already have a Supabase project? Enter credentials directly:
          </p>
          <ManualForm />
        </div>
      </div>

      {/* Footer links */}
      <div className="mt-6 flex items-center justify-center gap-4 text-xs text-[#555]">
        <a
          href="https://github.com/zerohuman-agency/zerohuman"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888] transition-colors"
        >
          GitHub
        </a>
        <span>·</span>
        <a
          href="/docs/SETUP.md"
          className="hover:text-[#888] transition-colors"
        >
          Setup docs
        </a>
        <span>·</span>
        <a
          href="https://supabase.com/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888] transition-colors"
        >
          Supabase dashboard
        </a>
      </div>
    </div>
  )
}
