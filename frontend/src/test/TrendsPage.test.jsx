import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import TrendsPage from '../pages/TrendsPage'
import { BackgroundTaskProvider } from '../App'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const { mockGetTrends, mockGetTrendAnalysis } = vi.hoisted(() => ({
  mockGetTrends: vi.fn().mockResolvedValue({
    items: [
      { id: '1', title: '重生千金复仇', source: 'hongguo', category: '重生', heat: 9500, tags: ['重生', '复仇'], description: '重生千金强势归来复仇' },
      { id: '2', title: '战神归来', source: 'tomato', category: '男频', heat: 8800, tags: ['战神', '逆袭'], description: '战神回归都市' },
    ],
    total: 2,
  }),
  mockGetTrendAnalysis: vi.fn().mockResolvedValue({
    total_count: 2,
    hot_keywords: ['重生', '复仇', '战神'],
    sources: { hongguo: 1, tomato: 1 },
    top_10: [
      { title: '重生千金复仇', source: 'hongguo', heat: 9500, tags: ['重生'] },
      { title: '战神归来', source: 'tomato', heat: 8800, tags: ['战神'] },
    ],
  }),
}))

vi.mock('../services/api', () => ({
  api: {
    getTrends: (...args) => mockGetTrends(...args),
    getTrendAnalysis: (...args) => mockGetTrendAnalysis(...args),
    getTrendsFetchStatus: vi.fn().mockResolvedValue({ fetching: false }),
    getRefreshSchedule: vi.fn().mockResolvedValue({ hour: 0, minute: 0, enabled: true }),
    setRefreshSchedule: vi.fn().mockResolvedValue({ hour: 0, minute: 0, enabled: true }),
  },
}))

function renderTrends() {
  return render(
    <BrowserRouter>
      <BackgroundTaskProvider>
        <TrendsPage />
      </BackgroundTaskProvider>
    </BrowserRouter>
  )
}

describe('TrendsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title', () => {
    renderTrends()
    expect(screen.getByText('热点趋势')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    renderTrends()
    expect(screen.getByText('正在抓取最新数据...')).toBeInTheDocument()
  })

  it('displays trend cards after loading', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    }, { timeout: 5000 })
    expect(screen.getAllByText('重生千金复仇').length).toBeGreaterThan(0)
    expect(screen.getAllByText('战神归来').length).toBeGreaterThan(0)
  })

  it('shows source filter buttons', () => {
    renderTrends()
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('红果短剧')).toBeInTheDocument()
    expect(screen.getByText('番茄小说')).toBeInTheDocument()
  })

  it('shows analysis summary', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    })
    // Total count badge shows the number
    expect(screen.getByText('总热点数')).toBeInTheDocument()
  })

  it('shows top 10 ranking', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    })
    expect(screen.getByText('热度排行 Top 10')).toBeInTheDocument()
  })

  it('has generate button on trend cards', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    })
    const buttons = screen.getAllByText(/基于此热点生成剧本/)
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('navigates to generate with trend context', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    })
    const buttons = screen.getAllByText(/基于此热点生成剧本/)
    fireEvent.click(buttons[0])
    expect(mockNavigate).toHaveBeenCalledWith('/generate', expect.objectContaining({
      state: expect.objectContaining({
        topic: '重生千金复仇',
      }),
    }))
  })

  it('shows hot keywords', async () => {
    renderTrends()
    await waitFor(() => {
      expect(screen.queryByText('正在抓取最新数据...')).not.toBeInTheDocument()
    })
    expect(screen.getByText('热门关键词')).toBeInTheDocument()
  })
})
