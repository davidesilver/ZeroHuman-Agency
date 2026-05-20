import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DeepResearchPage from './page'

vi.mock('@/lib/brand-context', () => ({
  useBrand: () => ({ activeBrand: { id: 'brand-1', name: 'Test Brand' } }),
}))

vi.mock('@/hooks/use-polling', () => ({
  // Mirror real hook: call cb once on mount only (not on every re-render)
  usePolling: (cb: () => void) => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { useEffect } = require('react')
    useEffect(() => { void cb() }, [])
  },
}))

vi.mock('@/components/ui/feature-gate', () => ({
  FeatureGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/ui/error-card', () => ({
  ErrorCard: ({ message }: { message: string }) => <div role="alert">{message}</div>,
}))

vi.mock('@/components/ui/empty-state', () => ({
  EmptyState: ({ message }: { message: string }) => <div>{message}</div>,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

const JOB_FIXTURE = {
  id: 'job-abc',
  topic: 'AI in healthcare',
  depth: 3,
  status: 'completed' as const,
  created_at: '2026-01-01T00:00:00Z',
}

describe('DeepResearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([JOB_FIXTURE]),
    })
  })

  it('renders page heading', async () => {
    render(<DeepResearchPage />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /deep research/i })).toBeInTheDocument()
    })
  })

  it('displays existing jobs after load', async () => {
    render(<DeepResearchPage />)
    await waitFor(() => {
      expect(screen.getByText('AI in healthcare')).toBeInTheDocument()
    })
  })

  it('submits a new research query', async () => {
    const user = userEvent.setup()
    // usePolling fires loadJobs immediately (call 1), POST is call 2, reload is call 3
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([JOB_FIXTURE]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ id: 'job-new' }) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([JOB_FIXTURE]) })

    render(<DeepResearchPage />)
    await waitFor(() => screen.getByRole('heading', { name: /deep research/i }))

    const input = screen.getByPlaceholderText(/ai trends/i)
    await user.type(input, 'Climate tech trends')
    await user.click(screen.getByRole('button', { name: /start research/i }))

    await waitFor(() => {
      const calls = mockFetch.mock.calls
      const postCall = calls.find(c => c[1]?.method === 'POST')
      expect(postCall).toBeTruthy()
      expect(JSON.parse(postCall![1].body)).toMatchObject({ topic: 'Climate tech trends' })
    })
  })

  it('shows error when fetch fails', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 503, json: () => Promise.resolve([]) })
    render(<DeepResearchPage />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
