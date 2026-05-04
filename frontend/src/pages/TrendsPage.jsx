import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function TrendsPage() {
  const navigate = useNavigate()
  const [trends, setTrends] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeSource, setActiveSource] = useState('all')
  const [refreshSchedule, setRefreshSchedule] = useState({ hour: 0, minute: 0, enabled: true })

  useEffect(() => {
    fetchTrends()
    api.getRefreshSchedule().then(setRefreshSchedule).catch(() => {})
  }, [activeSource])

  async function fetchTrends(forceRefresh = false) {
    setLoading(true)
    setError('')
    try {
      const [trendsRes, analysisRes] = await Promise.all([
        api.getTrends(activeSource, forceRefresh),
        api.getTrendAnalysis(forceRefresh),
      ])
      setTrends(trendsRes.items || [])
      setAnalysis(analysisRes)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleUseAsContext(trend) {
    navigate('/generate', {
      state: {
        topic: trend.title,
        trendContext: `热点灵感来源（仅供创意参考，请勿直接复制）:\n题材类型: ${(trend.tags || []).slice(0, 3).join('、')}\n热门元素: ${trend.description || trend.title}\n该热点的核心吸引力在于其题材设定和情感共鸣点`,
      },
    })
  }

  const sources = [
    { key: 'all', label: '全部' },
    { key: 'hongguo', label: '红果短剧' },
    { key: 'tomato', label: '番茄小说' },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">热点趋势</h1>
          <p className="text-sm text-ink-500 mt-1">聚合红果短剧、番茄小说当前热门内容</p>
        </div>
        <button
          className="btn btn-secondary text-sm"
          onClick={() => fetchTrends(true)}
          disabled={loading}
        >
          {loading ? (
            <span className="flex items-center gap-2"><span className="spinner" /> 刷新中...</span>
          ) : '刷新数据'}
        </button>
      </div>

      {/* Refresh Schedule */}
      <div className="flex items-center gap-3 text-sm">
        <span className="text-ink-500">自动刷新时间:</span>
        <select
          className="select w-auto"
          value={`${String(refreshSchedule.hour).padStart(2, '0')}:${String(refreshSchedule.minute).padStart(2, '0')}`}
          onChange={(e) => {
            const [h, m] = e.target.value.split(':').map(Number)
            const newSchedule = { ...refreshSchedule, hour: h, minute: m }
            setRefreshSchedule(newSchedule)
            api.setRefreshSchedule({ hour: h, minute: m }).catch(() => {})
          }}
        >
          {Array.from({ length: 24 }, (_, i) => {
            const label = `${String(i).padStart(2, '0')}:00`
            return <option key={label} value={label}>{label}</option>
          })}
        </select>
      </div>

      {/* Source Filter */}
      <div className="flex gap-1 bg-ink-50 p-1 rounded-lg w-fit">
        {sources.map((src) => (
          <button
            key={src.key}
            className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              activeSource === src.key
                ? 'bg-white text-ink-900 shadow-sm'
                : 'text-ink-500 hover:text-ink-700'
            }`}
            onClick={() => setActiveSource(src.key)}
          >
            {src.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Analysis Summary */}
      {analysis && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="text-xs text-ink-400 uppercase tracking-wider">总热点数</div>
            <div className="text-3xl font-bold text-ink-900 mt-1">{analysis.total_count}</div>
          </div>
          <div className="card p-4">
            <div className="text-xs text-ink-400 uppercase tracking-wider">热门关键词</div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {(analysis.hot_keywords || []).slice(0, 8).map((kw, i) => (
                <span key={i} className="badge badge-brand">{kw}</span>
              ))}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-xs text-ink-400 uppercase tracking-wider">数据来源</div>
            <div className="flex gap-4 mt-2">
              {Object.entries(analysis.sources || {}).map(([src, count]) => (
                <div key={src} className="text-sm">
                  <span className="text-ink-500">{src === 'hongguo' ? '红果' : '番茄'}</span>
                  <span className="ml-1 font-semibold text-ink-900">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Trends List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <span className="spinner" style={{ width: 32, height: 32 }} />
            <p className="text-sm text-ink-500 mt-3">正在抓取最新数据...</p>
          </div>
        </div>
      ) : trends.length === 0 ? (
        <div className="text-center py-20 text-ink-400">
          <p>暂无数据</p>
          <p className="text-sm mt-1">请稍后重试或检查网络连接</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {trends.map((trend, idx) => (
            <div
              key={trend.id || idx}
              className="card p-4 hover:border-ink-200 transition-colors animate-fade-in rounded-xl"
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-ink">
                      {trend.source === 'hongguo' ? '红果' : '番茄'}
                    </span>
                    {trend.category && (
                      <span className="text-xs text-ink-400">{trend.category}</span>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-ink-900 truncate">{trend.title}</h3>
                  {trend.description && (
                    <p className="text-xs text-ink-500 mt-1 line-clamp-2">{trend.description}</p>
                  )}
                  {trend.tags && trend.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {trend.tags.slice(0, 3).map((tag, i) => (
                        <span key={i} className="text-xs text-ink-400">#{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                {trend.heat > 0 && (
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs text-ink-400">热度</div>
                    <div className="text-sm font-bold text-brand-600">{trend.heat.toLocaleString()}</div>
                  </div>
                )}
              </div>
              <div className="mt-3 pt-3 border-t border-ink-50 flex justify-end">
                <button
                  className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                  onClick={() => handleUseAsContext(trend)}
                >
                  基于此热点生成剧本 &rarr;
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Top 10 */}
      {analysis?.top_10 && analysis.top_10.length > 0 && (
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-ink-900 mb-4">热度排行 Top 10</h2>
          <div className="space-y-2">
            {analysis.top_10.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 py-2 border-b border-ink-50 last:border-0"
              >
                <span className={`w-6 h-6 flex items-center justify-center text-xs font-bold rounded-lg ${
                  i < 3 ? 'bg-brand-100 text-brand-700' : 'bg-ink-50 text-ink-500'
                }`}>
                  {i + 1}
                </span>
                <span className="flex-1 text-sm text-ink-800">{item.title}</span>
                <span className="text-xs text-ink-400">{item.source === 'hongguo' ? '红果' : '番茄'}</span>
                <span className="text-sm font-medium text-brand-600">{item.heat.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
