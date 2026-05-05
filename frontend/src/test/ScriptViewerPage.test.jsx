import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import ScriptViewerPage from '../pages/ScriptViewerPage'
import { BackgroundTaskProvider } from '../App'

const { mockGetScript, mockCheckCopyright, mockRewriteScript } = vi.hoisted(() => ({
  mockGetScript: vi.fn().mockResolvedValue({
    id: 'test-123',
    title: '重生千金的复仇之路',
    genre: '重生',
    style: '古风',
    logline: '一句话概括',
    synopsis: '这是一个关于重生千金复仇的故事...',
    theme: '复仇与救赎',
    episodes: [
      {
        episode_number: 1,
        title: '浴火重生',
        summary: '女主在婚礼上被毒杀后重生',
        hook: '婚礼现场女主倒下',
        cliffhanger: '女主睁眼发现自己回到了三年前',
        key_conflict: '女主发现前世被害真相',
        emotional_arc: '震惊到愤怒到坚定',
        shots: [
          {
            shot_number: 1,
            shot_type: '特写',
            camera_movement: '固定',
            frame_content: '女主面部特写',
            dialogue: '我一定会回来的',
            duration: 3.0,
            video_prompt: '特写镜头，女主面部特写，眼神坚定，低声说"我一定会回来的"，语气充满决心和力量',
            hook_type: 'hook',
            hook_detail: '开头爆点',
          },
        ],
        total_duration: 90,
      },
      {
        episode_number: 2,
        title: '步步为营',
        summary: '女主开始布局复仇',
        shots: [],
      },
    ],
    characters: [
      {
        name: '苏婉儿',
        identity: '重生千金',
        age: '22',
        personality: '外柔内刚、心思缜密',
        appearance: '长发及腰，杏眼，肤白',
        clothing: '古风华服',
        arc: '从天真到成熟',
      },
    ],
    scenes: [
      { name: '皇宫大殿', description: '金碧辉煌的宫殿', atmosphere: '庄严' },
    ],
    props: [
      { name: '凤凰玉佩', description: '女主母亲留下的遗物' },
    ],
  }),
  mockCheckCopyright: vi.fn().mockResolvedValue({ risk_level: 'low', risk_score: 15, suggestions: [] }),
  mockRewriteScript: vi.fn().mockResolvedValue({ success: true, result: { title: '新标题' } }),
}))

vi.mock('../services/api', () => ({
  api: {
    getScript: (...args) => mockGetScript(...args),
    checkCopyright: (...args) => mockCheckCopyright(...args),
    rewriteScript: (...args) => mockRewriteScript(...args),
    getTrendsFetchStatus: vi.fn().mockResolvedValue({ fetching: false }),
  },
}))

function renderViewer(scriptId = 'test-123') {
  return render(
    <MemoryRouter initialEntries={[`/scripts/${scriptId}`]}>
      <BackgroundTaskProvider>
        <ScriptViewerPage />
      </BackgroundTaskProvider>
    </MemoryRouter>
  )
}

describe('ScriptViewerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    renderViewer()
    expect(document.querySelector('.spinner')).toBeInTheDocument()
  })

  it('displays script title after loading', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
  })

  it('shows genre badge', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生')).toBeInTheDocument()
    })
  })

  it('shows synopsis', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText(/这是一个关于重生千金复仇/)).toBeInTheDocument()
    })
  })

  it('shows episode tabs', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('第1集')).toBeInTheDocument()
      expect(screen.getByText('第2集')).toBeInTheDocument()
    })
  })

  it('shows first episode content by default', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText(/浴火重生/)).toBeInTheDocument()
      expect(screen.getByText(/女主在婚礼上被毒杀后重生/)).toBeInTheDocument()
    })
  })

  it('shows shot content', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getAllByText(/女主面部特写/).length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows hook type badges', async () => {
    renderViewer()
    await waitFor(() => {
      const hooks = screen.getAllByText('爆点钩子')
      expect(hooks.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows hook detail analysis for hook shots', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('开头爆点')).toBeInTheDocument()
    })
  })

  it('hook shot has colored background', async () => {
    renderViewer()
    await waitFor(() => {
      // The hook shot card should have red background
      const hookCards = document.querySelectorAll('.bg-red-50')
      expect(hookCards.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('switches to characters tab', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('角色'))
    expect(screen.getByText('苏婉儿')).toBeInTheDocument()
    expect(screen.getByText('重生千金')).toBeInTheDocument()
  })

  it('switches to scenes tab', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('场景'))
    expect(screen.getByText('皇宫大殿')).toBeInTheDocument()
  })

  it('switches to props tab', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('道具'))
    expect(screen.getByText('凤凰玉佩')).toBeInTheDocument()
  })

  it('shows rewrite button', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('改写剧本')).toBeInTheDocument()
    })
  })

  it('shows copyright check button', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('版权检测')).toBeInTheDocument()
    })
  })

  it('can expand character details', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('角色'))
    fireEvent.click(screen.getByText('苏婉儿'))
    await waitFor(() => {
      expect(screen.getByText('外貌描述')).toBeInTheDocument()
    })
  })

  it('opens rewrite panel when clicking rewrite button', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('改写剧本')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('改写剧本'))
    await waitFor(() => {
      expect(screen.getByText(/改写剧本整体/)).toBeInTheDocument()
    })
  })

  it('rewrite panel has textarea for instruction', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('改写剧本')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('改写剧本'))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/用自然语言描述/)).toBeInTheDocument()
    })
  })

  it('shows episode title in episode tab', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText(/浴火重生/)).toBeInTheDocument()
    })
  })

  it('switches between episodes', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('第2集')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('第2集'))
    await waitFor(() => {
      expect(screen.getByText(/步步为营/)).toBeInTheDocument()
    })
  })

  it('shows scene atmosphere', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('场景'))
    await waitFor(() => {
      expect(screen.getByText(/庄严/)).toBeInTheDocument()
    })
  })

  it('shows prop description', async () => {
    renderViewer()
    await waitFor(() => {
      expect(screen.getByText('重生千金的复仇之路')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('道具'))
    await waitFor(() => {
      expect(screen.getByText(/女主母亲留下的遗物/)).toBeInTheDocument()
    })
  })
})
