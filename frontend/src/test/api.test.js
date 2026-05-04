import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('getTrends fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0 }),
    })

    const { api } = await import('../services/api')
    await api.getTrends('all', false)

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/trends?source=all&force_refresh=false',
      expect.objectContaining({ headers: expect.any(Object) })
    )
  })

  it('generateScript sends POST with body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ task_id: 'abc123', status: 'generating' }),
    })

    const { api } = await import('../services/api')
    const result = await api.generateScript({
      topic: 'test',
      genre: '重生',
      episode_count: 3,
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/generate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ topic: 'test', genre: '重生', episode_count: 3 }),
      })
    )
    expect(result.task_id).toBe('abc123')
  })

  it('handles error responses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({ detail: '服务器错误' }),
    })

    const { api } = await import('../services/api')
    await expect(api.health()).rejects.toThrow('服务器错误')
  })

  it('scriptQA sends correct format', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: 's1', response: 'hi', is_complete: false }),
    })

    const { api } = await import('../services/api')
    await api.scriptQA({
      topic: '重生',
      genre: '重生',
      style: '古风',
      user_message: 'hello',
      history: [],
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/qa',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('rewriteScript sends correct format', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, result: {} }),
    })

    const { api } = await import('../services/api')
    await api.rewriteScript({
      script_id: 'test',
      target: 'overall',
      instruction: '改成更虐的',
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/rewrite',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('refreshTrends sends POST', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'started' }),
    })

    const { api } = await import('../services/api')
    await api.refreshTrends()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/trends/refresh',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('getConfigForTopic fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ genres: [], styles: [] }),
    })

    const { api } = await import('../services/api')
    await api.getConfigForTopic('重生千金')

    const calledUrl = mockFetch.mock.calls[0][0]
    expect(calledUrl).toContain('/api/config/topic/')
    expect(calledUrl).toContain(encodeURIComponent('重生千金'))
  })

  it('getTrendsFetchStatus fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ fetching: false }),
    })

    const { api } = await import('../services/api')
    await api.getTrendsFetchStatus()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/trends/fetch-status',
      expect.any(Object)
    )
  })

  it('getScript fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 'abc', title: 'test' }),
    })

    const { api } = await import('../services/api')
    await api.getScript('abc')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/abc',
      expect.any(Object)
    )
  })

  it('checkCopyright sends POST', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ risk_level: 'low', risk_score: 10 }),
    })

    const { api } = await import('../services/api')
    await api.checkCopyright('abc')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/abc/copyright-check',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('uploadNovel sends FormData', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ task_id: 'test', result: {} }),
    })

    const { api } = await import('../services/api')
    const file = new File(['test content'], 'novel.txt', { type: 'text/plain' })
    await api.uploadNovel(file, 8, '重生', '古风')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scripts/upload-novel',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('searchTrends fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: [] }),
    })

    const { api } = await import('../services/api')
    await api.searchTrends('复仇')

    const calledUrl = mockFetch.mock.calls[0][0]
    expect(calledUrl).toContain('/api/trends/search?keyword=')
    expect(calledUrl).toContain(encodeURIComponent('复仇'))
  })

  it('getRelatedTrends fetches correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ items: [] }),
    })

    const { api } = await import('../services/api')
    await api.getRelatedTrends('test-123')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/trends/related/test-123',
      expect.any(Object)
    )
  })
})
