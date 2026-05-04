import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App, { BackgroundTaskProvider } from '../App'

// Mock the API module
vi.mock('../services/api', () => ({
  api: {
    getTrendsFetchStatus: vi.fn().mockResolvedValue({ fetching: false }),
    getTrends: vi.fn().mockResolvedValue({ items: [] }),
    getTrendAnalysis: vi.fn().mockResolvedValue({ total_count: 0, hot_keywords: [], sources: {} }),
    getConfig: vi.fn().mockResolvedValue({ genres: [], styles: [] }),
    getRefreshSchedule: vi.fn().mockResolvedValue({ hour: 0, minute: 0, enabled: true }),
    setRefreshSchedule: vi.fn().mockResolvedValue({ hour: 0, minute: 0, enabled: true }),
  },
}))

// Silence act() warnings in tests
const originalError = console.error
beforeEach(() => {
  console.error = (...args) => {
    if (args[0]?.includes?.('not wrapped in act')) return
    originalError(...args)
  }
  // Mock localStorage to return a token
  localStorage.getItem.mockImplementation((key) => {
    if (key === 'token') return 'test-token';
    if (key === 'user') return JSON.stringify({ username: 'admin', is_admin: true });
    return null;
  });
  return () => { console.error = originalError }
})

function renderApp(ui = <App />, route = '/') {
  window.history.pushState({}, 'Test page', route)
  return render(
    <BrowserRouter>
      <BackgroundTaskProvider>
        {ui}
      </BackgroundTaskProvider>
    </BrowserRouter>
  )
}

describe('App', () => {
  it('renders header with logo', () => {
    renderApp()
    expect(screen.getByText('短剧创作')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    renderApp()
    // These texts may appear in both desktop and mobile nav
    expect(screen.getAllByText('热点趋势').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('生成剧本').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('小说改编').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('我的剧本').length).toBeGreaterThanOrEqual(1)
  })

  it('renders footer', () => {
    renderApp()
    expect(screen.getByText(/短剧创作工具/)).toBeInTheDocument()
  })

  it('highlights active nav item for home', () => {
    renderApp()
    const homeLinks = screen.getAllByText('热点趋势')
    // The desktop nav link should be highlighted
    const desktopLink = homeLinks.find(el => el.closest('.hidden.md\\:flex'))
    expect(desktopLink?.className).toContain('bg-brand-50')
  })
})
