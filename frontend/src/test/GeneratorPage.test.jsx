import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import GeneratorPage from '../pages/GeneratorPage'
import { BackgroundTaskProvider } from '../App'

// Mock API - use vi.hoisted to avoid hoisting issues
const {
  mockGenerateScript, mockGetScriptStatus, mockQA, mockGetConfig, mockGetTrends,
} = vi.hoisted(() => ({
  mockGenerateScript: vi.fn().mockResolvedValue({ task_id: 'test-123', status: 'generating' }),
  mockGetScriptStatus: vi.fn().mockResolvedValue({ status: 'generating', progress: 50, current_episode: 1, total_episodes: 3 }),
  mockQA: vi.fn().mockResolvedValue({ session_id: 's1', response: '你想写什么类型的故事？', is_complete: false }),
  mockGetConfig: vi.fn().mockResolvedValue({
    genres: [{ value: '重生', label: '重生', icon: '🔄', count: 10 }],
    styles: ['古风', '现代都市'],
  }),
  mockGetTrends: vi.fn().mockResolvedValue({
    items: [{ id: '1', title: '重生千金', source: 'hongguo', tags: ['重生'], description: 'test' }],
  }),
}))

vi.mock('../services/api', () => ({
  api: {
    generateScript: (...args) => mockGenerateScript(...args),
    getScriptStatus: (...args) => mockGetScriptStatus(...args),
    scriptQA: (...args) => mockQA(...args),
    getConfig: (...args) => mockGetConfig(...args),
    getConfigForTopic: vi.fn().mockResolvedValue({
      genres: [{ value: '重生', label: '重生', icon: '🔄', count: 10 }],
      styles: ['古风', '现代都市'],
    }),
    getTrends: (...args) => mockGetTrends(...args),
    getTrendsFetchStatus: vi.fn().mockResolvedValue({ fetching: false }),
  },
}))

function renderGenerator() {
  return render(
    <BrowserRouter>
      <BackgroundTaskProvider>
        <GeneratorPage />
      </BackgroundTaskProvider>
    </BrowserRouter>
  )
}

describe('GeneratorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders step 1 topic selection', async () => {
    renderGenerator()
    expect(screen.getByText('你想写什么故事？')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/重生千金/)).toBeInTheDocument()
  })

  it('shows suggested topics from trends', async () => {
    renderGenerator()
    await waitFor(() => {
      expect(screen.getByText('重生千金')).toBeInTheDocument()
    })
  })

  it('validates empty topic on next', async () => {
    renderGenerator()
    fireEvent.click(screen.getByText('下一步'))
    expect(screen.getByText('请输入或选择一个剧本主题')).toBeInTheDocument()
  })

  it('navigates to step 2 after entering topic', async () => {
    renderGenerator()
    const input = screen.getByPlaceholderText(/重生千金/)
    fireEvent.change(input, { target: { value: '我的测试剧本' } })
    fireEvent.click(screen.getByText('下一步'))
    expect(screen.getByText('选择题材和风格')).toBeInTheDocument()
  })

  it('selecting a trend topic fills form and goes to step 2', async () => {
    renderGenerator()
    await waitFor(() => {
      expect(screen.getByText('重生千金')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('重生千金'))
    expect(screen.getByText('选择题材和风格')).toBeInTheDocument()
  })

  it('shows progress steps', () => {
    renderGenerator()
    expect(screen.getByText('选择热点')).toBeInTheDocument()
    expect(screen.getByText('确定题材')).toBeInTheDocument()
    expect(screen.getByText('详细设定')).toBeInTheDocument()
    expect(screen.getByText('AI问答')).toBeInTheDocument()
    expect(screen.getByText('确认生成')).toBeInTheDocument()
  })
})
