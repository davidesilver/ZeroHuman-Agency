import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Sidebar } from './sidebar'

vi.mock('next/navigation', () => ({
  usePathname: () => '/content-hub',
}))

vi.mock('next/image', () => ({
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}))

vi.mock('./brand-switcher', () => ({
  BrandSwitcher: () => <div data-testid="brand-switcher" />,
}))

describe('Sidebar', () => {
  const logoutAction = vi.fn().mockResolvedValue(undefined)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders navigation links', () => {
    render(<Sidebar logoutAction={logoutAction} />)
    expect(screen.getByRole('link', { name: 'Content Hub' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()
    // "Research" and "Deep Research" both exist — check both
    expect(screen.getByRole('link', { name: 'Research' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Deep Research' })).toBeInTheDocument()
  })

  it('highlights the active route', () => {
    render(<Sidebar logoutAction={logoutAction} />)
    const activeLink = screen.getByRole('link', { name: /content hub/i })
    expect(activeLink).toHaveStyle({ background: 'var(--sidebar-accent)' })
  })

  it('renders logout button', () => {
    render(<Sidebar logoutAction={logoutAction} />)
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('renders brand switcher', () => {
    render(<Sidebar logoutAction={logoutAction} />)
    expect(screen.getByTestId('brand-switcher')).toBeInTheDocument()
  })
})
