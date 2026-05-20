import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import SettingsPage from './page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

vi.mock('@/lib/brand-context', () => ({
  useBrand: () => ({ activeBrand: { id: 'brand-1', name: 'Test Brand' }, brands: [] }),
}))

vi.mock('@/components/settings/email-provider-card', () => ({
  EmailProviderCard: () => <div data-testid="email-provider-card" />,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

const CONFIG_FIXTURE = {
  success: true,
  data: {
    api_keys: { anthropic: true, openrouter: false, serper: false, tavily: false, youtube: false, resend: false, firecrawl: false },
    research_tier: 'free',
    image_backends: { default_backend: 'replicate', default_model: 'flux-schnell', replicate: true, openai: false, pillo: false, openrouter: false, anthropic: false },
    postiz: { mode: 'disabled', api_url: '', api_key: false },
    alerts: { telegram_bot: false, telegram_chat: false },
    operations: { scheduler_secret: false, python_backend_url: 'http://localhost:8000', allowed_origins: '', scheduler_brand_id: '' },
    llm: { scoring_model: 'claude-haiku', auto_approve_score: 80, auto_reject_score: 30 },
    email: { from_email: '', from_name: '' },
    research: { dedup_threshold: 0.8, max_items_retriever: 10 },
    scheduler: { daily_pipeline: '0 7 * * *', feedback_loop: '0 8 * * *', publish_scheduled: '* * * * *' },
    budget: { daily_cap_usd: null },
    social: { linkedin: false, twitter: false, instagram: false, tiktok: false },
  },
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/system/config'))           return Promise.resolve({ ok: true, json: () => Promise.resolve(CONFIG_FIXTURE) })
      if (url.includes('/api/system/llm-routing'))      return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: false }) })
      if (url.includes('/api/brands'))                  return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, data: [] }) })
      if (url.includes('/api/llm/providers/metrics'))   return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  it('renders system status section after config loads', async () => {
    render(<SettingsPage />)
    await waitFor(() => {
      expect(screen.getByText(/system status/i)).toBeInTheDocument()
    })
  })

  it('shows LLM configured when anthropic key is set', async () => {
    render(<SettingsPage />)
    await waitFor(() => {
      expect(screen.getByText(/1\/2 providers/i)).toBeInTheDocument()
    })
  })

  it('handles config fetch failure gracefully', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/llm/providers/metrics')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      return Promise.reject(new Error('network error'))
    })
    render(<SettingsPage />)
    // Component stays in loading state when config fetch fails
    await waitFor(() => {
      expect(screen.getByText(/loading system status/i)).toBeInTheDocument()
    })
  })

  it('renders Add Brand button', async () => {
    render(<SettingsPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add brand/i })).toBeInTheDocument()
    })
  })
})
