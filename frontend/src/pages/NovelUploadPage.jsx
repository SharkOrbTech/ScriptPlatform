import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function NovelUploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [params, setParams] = useState({
    episode_count: 8,
    genre: 'rebirth',
    style: '古风',
  })

  function handleFileChange(e) {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
      setError('')
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) {
      setError('请选择小说文件')
      return
    }

    setUploading(true)
    setError('')

    try {
      const result = await api.uploadNovel(file, params)
      if (result.result) {
        navigate('/scripts/' + result.task_id, { state: { script: result.result } })
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink-900">小说改编</h1>
        <p className="text-sm text-ink-500 mt-1">
          上传完整小说，改编为多集短剧剧本
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        {/* File Upload */}
        <div>
          <label className="label">上传小说文件</label>
          <div
            className="border-2 border-dashed border-ink-200 rounded-lg p-8 text-center cursor-pointer hover:border-ink-300 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            {file ? (
              <div>
                <div className="text-sm font-medium text-ink-900">{file.name}</div>
                <div className="text-xs text-ink-400 mt-1">
                  {(file.size / 1024).toFixed(1)} KB
                </div>
              </div>
            ) : (
              <div>
                <div className="text-ink-400 mb-2">
                  <svg className="w-8 h-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16v-8m0 0l-3 3m3-3l3 3M3 16v2a2 2 0 002 2h14a2 2 0 002-2v-2" />
                  </svg>
                </div>
                <p className="text-sm text-ink-500">点击选择文件或拖拽到此处</p>
                <p className="text-xs text-ink-400 mt-1">支持 .txt .docx 格式</p>
              </div>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.docx,.doc"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        </div>

        {/* Parameters */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="label">目标集数</label>
            <select
              className="select"
              value={params.episode_count}
              onChange={(e) => setParams({ ...params, episode_count: Number(e.target.value) })}
            >
              {[3, 5, 8, 10, 12, 15].map((n) => (
                <option key={n} value={n}>{n}集</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">题材类型</label>
            <select
              className="select"
              value={params.genre}
              onChange={(e) => setParams({ ...params, genre: e.target.value })}
            >
              <option value="rebirth">重生</option>
              <option value="revenge">复仇</option>
              <option value="romance">甜宠</option>
              <option value="fantasy">玄幻</option>
              <option value="urban">都市</option>
              <option value="period">古装</option>
            </select>
          </div>
          <div>
            <label className="label">漫剧风格</label>
            <select
              className="select"
              value={params.style}
              onChange={(e) => setParams({ ...params, style: e.target.value })}
            >
              {['古风', '现代', '日漫', '韩漫', '写实'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Tips */}
        <div className="bg-ink-50 rounded-lg p-4 text-sm text-ink-600 space-y-1.5">
          <p className="font-medium text-ink-700">使用提示：</p>
          <ul className="list-disc list-inside space-y-0.5 text-xs">
            <li>支持TXT纯文本和Word文档格式</li>
            <li>文件大小上限 500KB（约20-30万字）</li>
            <li>AI会自动提取主要角色和剧情线</li>
            <li>建议先使用短篇测试效果</li>
          </ul>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          className="btn btn-primary w-full py-3 text-base"
          disabled={uploading || !file}
        >
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="spinner" /> 正在改编中...
            </span>
          ) : '开始改编'}
        </button>
      </form>
    </div>
  )
}
