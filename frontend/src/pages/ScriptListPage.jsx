import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

export default function ScriptListPage() {
  const [scripts, setScripts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchScripts()
  }, [])

  async function fetchScripts() {
    setLoading(true)
    try {
      const data = await api.listScripts()
      setScripts(data.items || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">我的剧本</h1>
          <p className="text-sm text-ink-500 mt-1">已生成的剧本列表</p>
        </div>
        <Link to="/generate" className="btn btn-primary text-sm no-underline">
          新建剧本
        </Link>
      </div>

      {scripts.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-ink-400 mb-4">还没有生成过剧本</p>
          <Link to="/generate" className="btn btn-primary no-underline">
            开始创作
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {scripts.map((script) => (
            <Link
              key={script.id}
              to={`/scripts/${script.id}`}
              className="card p-4 hover:border-ink-200 transition-colors block no-underline"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-ink-900">{script.title}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="badge badge-brand">{script.genre}</span>
                    <span className="text-xs text-ink-400">{script.episode_count}集</span>
                    {script.logline && (
                      <span className="text-xs text-ink-500 truncate max-w-md">{script.logline}</span>
                    )}
                  </div>
                </div>
                <div className="text-xs text-ink-400">
                  {script.created_at ? new Date(script.created_at).toLocaleDateString('zh-CN') : ''}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
