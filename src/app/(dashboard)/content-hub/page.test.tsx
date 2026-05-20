import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ContentHubPage from './page'

vi.mock('next/navigation', () => ({
  useSearchParams: () => ({ get: () => null }),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

vi.mock('@/components/content/draft-card', () => ({
  DraftCard: ({ draft }: { draft: { title: string | null } }) => (
    <div data-testid="draft-card">{draft.title}</div>
  ),
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

const DRAFT_FIXTURE = {
  id: 'abc123',
  title: 'Test Draft Title',
  body: 'body text',
  platform: 'linkedin',
  content_type: 'post',
  status: 'draft',
  version: 1,
  god_mode_result: null,
  created_at: '2026-01-01T00:00:00Z',
  media_urls: null,
}

describe('ContentHubPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      json: () => Promise.resolve({ success: true, data: { drafts: [DRAFT_FIXTURE] } }),
    })
  })

  it('renders page heading', async () => {
    render(<ContentHubPage />)
    expect(screen.getByRole('heading', { name: /content hub/i })).toBeInTheDocument()
  })

  it('renders draft cards after fetch', async () => {
    render(<ContentHubPage />)
    await waitFor(() => {
      expect(screen.getByTestId('draft-card')).toBeInTheDocument()
      expect(screen.getByText('Test Draft Title')).toBeInTheDocument()
    })
  })

  it('renders status filter tabs', () => {
    render(<ContentHubPage />)
    expect(screen.getByText('DRAFTS')).toBeInTheDocument()
    expect(screen.getByText('APPROVED')).toBeInTheDocument()
    expect(screen.getByText('PUBLISHED')).toBeInTheDocument()
  })

  it('shows empty state when fetch returns no drafts', async () => {
    mockFetch.mockResolvedValue({
      json: () => Promise.resolve({ success: true, data: { drafts: [] } }),
    })
    render(<ContentHubPage />)
    await waitFor(() => {
      expect(screen.queryByTestId('draft-card')).not.toBeInTheDocument()
    })
  })
})
