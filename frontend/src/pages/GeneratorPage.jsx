import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'
import { useBackgroundTask } from '../App'

export default function GeneratorPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { taskId: urlTaskId } = useParams()
  const pollRef = useRef(null)
  const { addTask, removeTask } = useBackgroundTask()

  const [config, setConfig] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState(urlTaskId || '')
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [notification, setNotification] = useState('')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  // Multi-round question state
  const [step, setStep] = useState(1) // 1: topic, 2: genre, 3: details, 4: qa, 5: confirm
  const [suggestedTopics, setSuggestedTopics] = useState([])

  // Q&A state
  const [qaSessionId, setQaSessionId] = useState('')
  const [qaHistory, setQaHistory] = useState([])
  const [qaInput, setQaInput] = useState('')
  const [qaLoading, setQaLoading] = useState(false)
  const [qaSummary, setQaSummary] = useState(null)
  const [qaOptions, setQaOptions] = useState([])
  const qaEndRef = useRef(null)

  const [form, setForm] = useState({
    topic: '',
    genre: '',
    episode_count: 8,
    episode_duration: 90,
    target_audience: '18-35岁女性',
    style: '古风',
    special_requirements: '',
    trend_context: '',
  })

  // Load config with dynamic genres
  useEffect(() => {
    api.getConfig().then((data) => {
      setConfig(data)
      if (data.genres?.length > 0 && !form.genre) {
        setForm(prev => ({ ...prev, genre: data.genres[0].value }))
      }
    }).catch(() => {})
  }, [])

  // Reload genres when topic changes
  useEffect(() => {
    if (form.topic.trim().length >= 2) {
      api.getConfigForTopic(form.topic).then((data) => {
        if (data.genres?.length > 0) {
          setConfig(prev => ({
            ...prev,
            genres: data.genres,
            styles: data.styles?.length > 0 ? data.styles : prev?.styles,
          }))
          // Auto-select first genre if current genre not in new list
          if (!data.genres.find(g => g.value === form.genre)) {
            setForm(prev => ({ ...prev, genre: data.genres[0].value }))
          }
        }
      }).catch(() => {})
    }
  }, [form.topic])

  // Load trending topics for suggestions
  useEffect(() => {
    api.getTrends().then((data) => {
      if (data.items?.length > 0) {
        setSuggestedTopics(data.items.slice(0, 12))
      }
    }).catch(() => {})
  }, [])

  // Auto-scroll Q&A chat
  useEffect(() => {
    if (qaEndRef.current) {
      qaEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [qaHistory])

  // Pre-fill from navigation state
  useEffect(() => {
    if (location.state) {
      setForm((prev) => ({
        ...prev,
        topic: location.state.topic || prev.topic,
        trend_context: location.state.trendContext || prev.trend_context,
      }))
      if (location.state.topic) setStep(2)
    }
  }, [location.state])

  // Poll status
  useEffect(() => {
    if (taskId && generating) {
      pollStatus()
      pollRef.current = setInterval(pollStatus, 3000)
      return () => clearInterval(pollRef.current)
    }
  }, [taskId, generating])

  // Elapsed time timer
  useEffect(() => {
    if (generating) {
      setElapsedSeconds(0)
      const timer = setInterval(() => setElapsedSeconds(s => s + 1), 1000)
      return () => clearInterval(timer)
    }
  }, [generating])

  useEffect(() => {
    if (urlTaskId && !generating) {
      setTaskId(urlTaskId)
      setGenerating(true)
      addTask(`gen-${urlTaskId}`, '正在生成剧本...')
    }
  }, [urlTaskId])

  async function pollStatus() {
    try {
      const data = await api.getScriptStatus(taskId)
      setStatus(data)
      if (data.status === 'completed' || data.status === 'failed') {
        setGenerating(false)
        clearInterval(pollRef.current)
        removeTask(`gen-${taskId}`)
        if (data.status === 'completed') {
          setNotification('剧本生成完成！')
          setTimeout(() => setNotification(''), 5000)
          navigate(`/scripts/${taskId}`, { state: { script: data.script } })
        }
      }
    } catch (err) {}
  }

  function selectTopic(topic) {
    const tags = topic.tags || []
    setForm(prev => ({
      ...prev,
      topic: topic.title,
      trend_context: `热点灵感来源（仅供创意参考，请勿直接复制）:\n题材类型: ${tags.slice(0, 3).join('、')}\n热门元素: ${topic.description || topic.title}\n该热点的核心吸引力在于其题材设定和情感共鸣点`,
    }))
    // Load topic-specific genres + auto-select audience and style
    api.getConfigForTopic(topic.title).then((data) => {
      if (data.genres?.length > 0) {
        setConfig(prev => ({
          ...prev,
          genres: data.genres,
          styles: data.styles?.length > 0 ? data.styles : prev?.styles,
        }))
        setForm(prev => ({
          ...prev,
          genre: data.genres[0].value,
          target_audience: data.suggested_audience || prev.target_audience,
          style: data.suggested_style || prev.style,
        }))
      }
    }).catch(() => {})
    setStep(2)
  }

  function nextStep() {
    if (step === 1 && !form.topic.trim()) {
      setError('请输入或选择一个剧本主题')
      return
    }
    setError('')
    if (step === 3) {
      // Going to Q&A step - start the conversation
      setStep(4)
      if (qaHistory.length === 0) {
        startQA()
      }
    } else if (step < 5) {
      setStep(step + 1)
    }
  }

  async function handleSubmit() {
    if (!form.topic.trim()) {
      setError('请输入剧本主题')
      return
    }
    setError('')
    setGenerating(true)
    setStatus(null)

    try {
      const res = await api.generateScript(form)
      setTaskId(res.task_id)
      addTask(`gen-${res.task_id}`, '正在生成剧本...')
      navigate(`/generate/${res.task_id}`, { replace: true })
    } catch (err) {
      setError(err.message)
      setGenerating(false)
    }
  }

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function startQA() {
    setQaLoading(true)
    setQaOptions([])
    try {
      const res = await api.scriptQA({
        session_id: qaSessionId,
        topic: form.topic,
        genre: form.genre,
        style: form.style,
        user_message: '',
        history: [],
      })
      setQaSessionId(res.session_id)
      setQaHistory([{ role: 'assistant', content: res.response }])
      setQaOptions(res.options || [])
      if (res.is_complete) {
        setQaSummary(res.summary)
        setQaOptions([])
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setQaLoading(false)
    }
  }

  async function sendQAMessage(userMsg) {
    const msg = userMsg || qaInput.trim()
    if (!msg || qaLoading) return
    setQaInput('')
    const newHistory = [...qaHistory, { role: 'user', content: msg }]
    setQaHistory(newHistory)
    setQaLoading(true)
    setQaOptions([])

    try {
      const res = await api.scriptQA({
        session_id: qaSessionId,
        topic: form.topic,
        genre: form.genre,
        style: form.style,
        user_message: msg,
        history: newHistory,
      })
      setQaHistory([...newHistory, { role: 'assistant', content: res.response }])
      setQaOptions(res.options || [])
      if (res.is_complete) {
        setQaSummary(res.summary)
        setQaOptions([])
      }
    } catch (err) {
      setQaHistory([...newHistory, { role: 'assistant', content: `抱歉，出错了: ${err.message}` }])
    } finally {
      setQaLoading(false)
    }
  }

  function applyQASummary() {
    if (!qaSummary) return
    setForm(prev => ({
      ...prev,
      special_requirements: [
        prev.special_requirements,
        qaSummary.core_conflict ? `核心冲突: ${qaSummary.core_conflict}` : '',
        qaSummary.character_setup ? `角色设定: ${qaSummary.character_setup}` : '',
        qaSummary.hook_design ? `钩子设计: ${qaSummary.hook_design}` : '',
        qaSummary.emotional_arc ? `情感走向: ${qaSummary.emotional_arc}` : '',
      ].filter(Boolean).join('\n'),
    }))
  }

  const genres = config?.genres || []
  const styles = config?.styles || ['古风', '现代都市', '赛博朋克', '日漫', '韩漫', '写实']

  return (
    <div className="space-y-6">
      {/* Notification Toast */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-xl shadow-lg animate-fade-in flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {notification}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-ink-900">生成剧本</h1>
        <p className="text-sm text-ink-500 mt-1">
          设定参数，生成完整的多集短剧剧本
        </p>
      </div>

      {/* Progress Steps */}
      {!generating && !status?.script && (
        <div className="flex items-center gap-2 text-xs">
          {['选择热点', '确定题材', '详细设定', 'AI问答', '确认生成'].map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
                step > i + 1 ? 'bg-brand-600 text-white' :
                step === i + 1 ? 'bg-brand-100 text-brand-700 border border-brand-300' :
                'bg-ink-100 text-ink-400'
              }`}>
                {step > i + 1 ? '✓' : i + 1}
              </div>
              <span className={step === i + 1 ? 'text-ink-900 font-medium' : 'text-ink-400'}>{label}</span>
              {i < 4 && <span className="text-ink-200 mx-1">→</span>}
            </div>
          ))}
        </div>
      )}

      {/* Step 1: Topic Selection */}
      {!generating && step === 1 && (
        <div className="card p-6 animate-fade-in">
          <h2 className="text-lg font-semibold text-ink-900 mb-1">你想写什么故事？</h2>
          <p className="text-sm text-ink-500 mb-4">输入主题，或从当前热点中选择</p>

          <input
            type="text"
            className="input mb-4"
            placeholder="例如：重生千金的复仇之路、战神归来发现女儿住狗窝..."
            value={form.topic}
            onChange={(e) => handleChange('topic', e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && nextStep()}
          />

          {suggestedTopics.length > 0 && (
            <div>
              <div className="text-xs font-medium text-ink-500 mb-2">当前热点（点击选择）</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestedTopics.map((topic, i) => (
                  <button
                    key={i}
                    className="text-left p-3 border border-ink-100 rounded-lg hover:border-brand-300 hover:bg-brand-50 transition-colors"
                    onClick={() => selectTopic(topic)}
                  >
                    <div className="text-sm font-medium text-ink-900 truncate">{topic.title}</div>
                    <div className="text-xs text-ink-400 mt-0.5 truncate">
                      {(topic.tags || []).slice(0, 3).join(' / ')}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && <div className="text-sm text-red-600 mt-3">{error}</div>}

          <div className="flex justify-end mt-4">
            <button className="btn btn-primary" onClick={nextStep}>下一步</button>
          </div>
        </div>
      )}

      {/* Step 2: Genre & Style */}
      {!generating && step === 2 && (
        <div className="card p-6 animate-fade-in">
          <h2 className="text-lg font-semibold text-ink-900 mb-1">选择题材和风格</h2>
          <p className="text-sm text-ink-500 mb-4">基于当前热点趋势，以下是热门题材</p>

          <div className="mb-4">
            <label className="label">题材类型</label>
            <div className="flex flex-wrap gap-2">
              {genres.map((g) => (
                <button
                  key={g.value}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                    form.genre === g.value
                      ? 'bg-brand-600 text-white border-brand-600'
                      : 'bg-white text-ink-700 border-ink-200 hover:border-brand-300'
                  }`}
                  onClick={() => handleChange('genre', g.value)}
                >
                  {g.icon} {g.label}
                  {g.count > 0 && <span className="ml-1 text-xs opacity-60">({g.count})</span>}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <label className="label">漫剧风格</label>
            <div className="flex flex-wrap gap-2">
              {styles.map((s) => (
                <button
                  key={s}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                    form.style === s
                      ? 'bg-brand-600 text-white border-brand-600'
                      : 'bg-white text-ink-700 border-ink-200 hover:border-brand-300'
                  }`}
                  onClick={() => handleChange('style', s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="label">集数</label>
              <select className="select" value={form.episode_count} onChange={(e) => handleChange('episode_count', Number(e.target.value))}>
                {[3, 5, 8, 10, 12, 15, 20, 30, 50, 80, 100, 120, 150, 200].map(n => <option key={n} value={n}>{n}集</option>)}
              </select>
            </div>
            <div>
              <label className="label">每集时长</label>
              <select className="select" value={form.episode_duration} onChange={(e) => handleChange('episode_duration', Number(e.target.value))}>
                {[30, 60, 90, 120, 180].map(n => <option key={n} value={n}>{n}秒</option>)}
              </select>
            </div>
            <div>
              <label className="label">目标受众</label>
              <select className="select" value={form.target_audience} onChange={(e) => handleChange('target_audience', e.target.value)}>
                {['18-35岁女性', '18-35岁男性', '全年龄', '青少年', '35岁以上'].map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>

          <div className="flex justify-between">
            <button className="btn btn-ghost" onClick={() => setStep(1)}>上一步</button>
            <button className="btn btn-primary" onClick={nextStep}>下一步</button>
          </div>
        </div>
      )}

      {/* Step 3: Details */}
      {!generating && step === 3 && (
        <div className="card p-6 animate-fade-in">
          <h2 className="text-lg font-semibold text-ink-900 mb-1">补充细节（可选）</h2>
          <p className="text-sm text-ink-500 mb-4">提供更多细节可以让AI生成更符合预期的剧本</p>

          <div className="mb-4">
            <label className="label">特殊要求</label>
            <textarea
              className="textarea"
              rows={4}
              placeholder="例如：要有闪婚情节、女主是穿越的、需要多条感情线、要有打脸逆袭..."
              value={form.special_requirements}
              onChange={(e) => handleChange('special_requirements', e.target.value)}
            />
          </div>

          {form.trend_context && (
            <div className="bg-brand-50 border border-brand-100 rounded-lg p-3 mb-4">
              <div className="text-xs font-medium text-brand-700 mb-1">热点参考</div>
              <p className="text-sm text-ink-700 whitespace-pre-wrap">{form.trend_context}</p>
            </div>
          )}

          <div className="flex justify-between">
            <button className="btn btn-ghost" onClick={() => setStep(2)}>上一步</button>
            <button className="btn btn-primary" onClick={nextStep}>下一步: AI问答</button>
          </div>
        </div>
      )}

      {/* Step 4: AI Q&A */}
      {!generating && step === 4 && (
        <div className="card p-6 animate-fade-in">
          <h2 className="text-lg font-semibold text-ink-900 mb-1">AI编剧问答</h2>
          <p className="text-sm text-ink-500 mb-4">回答AI的问题，帮助明确创作方向（可跳过直接生成）</p>

          <div className="border border-ink-100 rounded-lg p-4 max-h-[400px] overflow-y-auto mb-4 space-y-4">
            {qaHistory.length === 0 && qaLoading && (
              <div className="flex items-center gap-2 text-ink-400 text-sm">
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                AI正在思考...
              </div>
            )}
            {qaHistory.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-ink-50 text-ink-800'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {qaLoading && qaHistory.length > 0 && (
              <div className="flex justify-start">
                <div className="bg-ink-50 rounded-lg px-4 py-2.5 text-sm text-ink-400">
                  <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                </div>
              </div>
            )}
            <div ref={qaEndRef} />
          </div>

          {/* Q&A Summary */}
          {qaSummary && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
              <div className="text-sm font-medium text-green-800 mb-1">信息已充分！</div>
              <p className="text-xs text-green-700">AI已收集到足够的创作信息，可以直接进入确认步骤。</p>
            </div>
          )}

          {/* Clickable Options */}
          {qaOptions.length > 0 && !qaLoading && (
            <div className="grid grid-cols-2 gap-2 mb-4">
              {qaOptions.map((opt) => (
                <button
                  key={opt.key}
                  className="text-left p-3 border border-ink-200 rounded-lg hover:border-brand-400 hover:bg-brand-50 transition-colors"
                  onClick={() => sendQAMessage(`${opt.key}. ${opt.text}`)}
                >
                  <span className="text-xs font-bold text-brand-600 mr-1">{opt.key}.</span>
                  <span className="text-sm text-ink-800">{opt.text}</span>
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              className="input flex-1"
              placeholder={qaLoading ? '等待AI回复...' : '输入自定义回答或选择上方选项...'}
              value={qaInput}
              onChange={(e) => setQaInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendQAMessage()}
              disabled={qaLoading}
            />
            <button className="btn btn-primary" onClick={() => sendQAMessage()} disabled={qaLoading || !qaInput.trim()}>
              发送
            </button>
          </div>

          <div className="flex justify-between">
            <button className="btn btn-ghost" onClick={() => setStep(3)}>上一步</button>
            <div className="flex gap-2">
              <button className="btn btn-ghost text-sm" onClick={() => { applyQASummary(); setStep(5) }}>
                跳过问答
              </button>
              <button className="btn btn-primary" onClick={() => { applyQASummary(); setStep(5) }}>
                下一步: 确认生成
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Confirm */}
      {!generating && step === 5 && (
        <div className="card p-6 animate-fade-in">
          <h2 className="text-lg font-semibold text-ink-900 mb-4">确认生成</h2>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-ink-50">
              <span className="text-ink-500">主题</span>
              <span className="text-ink-900 font-medium">{form.topic}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-ink-50">
              <span className="text-ink-500">题材</span>
              <span className="text-ink-900">{form.genre}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-ink-50">
              <span className="text-ink-500">风格</span>
              <span className="text-ink-900">{form.style}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-ink-50">
              <span className="text-ink-500">集数/时长</span>
              <span className="text-ink-900">{form.episode_count}集 × {form.episode_duration}秒</span>
            </div>
            <div className="flex justify-between py-2 border-b border-ink-50">
              <span className="text-ink-500">目标受众</span>
              <span className="text-ink-900">{form.target_audience}</span>
            </div>
            {form.special_requirements && (
              <div className="flex justify-between py-2 border-b border-ink-50">
                <span className="text-ink-500">特殊要求</span>
                <span className="text-ink-900 text-right max-w-xs truncate">{form.special_requirements}</span>
              </div>
            )}
          </div>

          <div className="bg-ink-50 rounded-lg p-3 mt-4 text-xs text-ink-500">
            AI将生成：完整剧本 + 每集分镜脚本 + 角色三视图提示词 + 场景/道具AI绘图提示词 + 版权风险检测
          </div>

          {error && <div className="text-sm text-red-600 mt-3">{error}</div>}

          <div className="flex justify-between mt-4">
            <button className="btn btn-ghost" onClick={() => setStep(4)}>上一步</button>
            <button className="btn btn-primary px-8" onClick={handleSubmit}>开始生成</button>
          </div>
        </div>
      )}

      {/* Generating Progress */}
      {generating && (
        <div className="card p-8 animate-fade-in">
          <div className="text-center mb-6">
            <div className="mb-4">
              <span className="spinner" style={{ width: 48, height: 48, borderWidth: 3 }} />
            </div>
            <h2 className="text-lg font-semibold text-ink-900 mb-2">正在生成剧本</h2>
            <p className="text-sm text-ink-600 font-medium">
              {status?.current_phase || '正在初始化AI引擎...'}
            </p>
          </div>

          {/* Phase Stepper */}
          <div className="flex items-center justify-between mb-6 max-w-lg mx-auto">
            {[
              { key: 'plan', label: '策划' },
              { key: 'character', label: '角色' },
              { key: 'episode', label: '剧集' },
              { key: 'assemble', label: '组装' },
            ].map((phase, i, arr) => {
              const progress = status?.progress || 0
              const phaseProgress = [15, 20, 95, 100]
              const isActive = progress < phaseProgress[i] && (i === 0 || progress >= phaseProgress[i - 1])
              const isDone = progress >= phaseProgress[i]
              return (
                <div key={phase.key} className="flex items-center flex-1">
                  <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                      isDone ? 'bg-brand-500 text-white' : isActive ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-500' : 'bg-ink-100 text-ink-400'
                    }`}>
                      {isDone ? '✓' : i + 1}
                    </div>
                    <span className={`text-xs mt-1 ${isDone || isActive ? 'text-ink-700' : 'text-ink-400'}`}>{phase.label}</span>
                  </div>
                  {i < arr.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-2 mt-[-16px] ${isDone ? 'bg-brand-500' : 'bg-ink-100'}`} />
                  )}
                </div>
              )
            })}
          </div>

          {/* Progress Bar */}
          <div className="w-full max-w-lg mx-auto bg-ink-100 rounded-full h-2 mb-2">
            <div
              className="bg-brand-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${status?.progress || 0}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-ink-400 max-w-lg mx-auto">
            <span>{Math.round(status?.progress || 0)}% 完成</span>
            <span>已用时 {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, '0')}</span>
          </div>

          <p className="text-xs text-ink-400 mt-4 text-center">
            生成将在后台继续进行，您可以浏览其他页面
          </p>
          <div className="flex justify-center gap-3 mt-4">
            <button className="btn btn-ghost text-sm" onClick={() => navigate('/')}>
              返回首页
            </button>
            <button className="btn btn-ghost text-sm" onClick={() => navigate('/scripts')}>
              我的剧本
            </button>
          </div>
        </div>
      )}

      {/* Error state */}
      {status?.status === 'failed' && (
        <div className="card p-6 text-center">
          <div className="text-red-500 text-4xl mb-4">!</div>
          <h2 className="text-lg font-semibold text-ink-900 mb-2">生成失败</h2>
          <p className="text-sm text-red-600 mb-4">{status.error}</p>
          <button className="btn btn-secondary" onClick={() => { setGenerating(false); setStatus(null); setTaskId(''); setStep(1) }}>
            重新尝试
          </button>
        </div>
      )}
    </div>
  )
}
