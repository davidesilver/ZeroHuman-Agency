import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GettingStartedBanner } from './getting-started'

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

const INCOMPLETE_STATUS: Record<string, { data: unknown }> = {
  config: { data: {} },
  brands: { data: [] },
  facts: { data: [] },
  research: { data: [] },
  drafts: { data: [] },
}

function setupFetch(overrides: Partial<typeof INCOMPLETE_STATUS> = {}) {
  const status = { ...INCOMPLETE_STATUS, ...overrides }
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/api/system/config'))   return Promise.resolve({ json: () => Promise.resolve(status.config) })
    if (url.includes('/api/brands'))          return Promise.resolve({ json: () => Promise.resolve(status.brands) })
    if (url.includes('/api/memory/facts'))    return Promise.resolve({ json: () => Promise.resolve(status.facts) })
    if (url.includes('/api/research'))        return Promise.resolve({ json: () => Promise.resolve(status.research) })
    if (url.includes('/api/content'))         return Promise.resolve({ json: () => Promise.resolve(status.drafts) })
    return Promise.reject(new Error(`unmocked fetch: ${url}`))
  })
}

describe('GettingStartedBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows progress counter after fetch', async () => {
    setupFetch()
    render(<GettingStartedBanner />)
    await waitFor(() => {
      expect(screen.getByText(/0 \/ 5 complete/i)).toBeInTheDocument()
    })
  })

  it('marks brand step done when brands exist', async () => {
    setupFetch({ brands: { data: [{ id: '1', name: 'ACME' }] } })
    render(<GettingStartedBanner />)
    await waitFor(() => {
      expect(screen.getByText(/create your first brand/i)).toBeInTheDocument()
    })
  })

  it('dismisses banner when X is clicked', async () => {
    setupFetch()
    const user = userEvent.setup()
    render(<GettingStartedBanner />)
    await waitFor(() => screen.getByTitle('Dismiss'))
    await user.click(screen.getByTitle('Dismiss'))
    expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument()
    expect(localStorage.getItem('getting_started_dismissed')).toBe('true')
  })

  it('stays hidden when already dismissed', () => {
    localStorage.setItem('getting_started_dismissed', 'true')
    render(<GettingStartedBanner />)
    expect(screen.queryByText(/getting started/i)).not.toBeInTheDocument()
  })
})
