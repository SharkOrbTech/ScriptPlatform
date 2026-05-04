import { useState, useEffect } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import { api } from '../services/api'
import { exportToMarkdown, exportToDocx } from '../services/exportUtils'

export default function ScriptViewerPage() {
  const { scriptId } = useParams()
  const location = useLocation()
  const [script, setScript] = useState(location.state?.script || null)
  const [loading, setLoading] = useState(!script)
  const [activeEpisode, setActiveEpisode] = useState(1)
  const [activeTab, setActiveTab] = useState('episodes') // episodes, characters, scenes, props
  const [showAllShots, setShowAllShots] = useState(false)
  const [copyrightResult, setCopyrightResult] = useState(script?.copyright_risk || null)
  const [checkingCopyright, setCheckingCopyright] = useState(false)
  const [expandedChar, setExpandedChar] = useState(null)

  // Rewrite state
  const [rewriteTarget, setRewriteTarget] = useState(null) // {target, targetName}
  const [rewriteInstruction, setRewriteInstruction] = useState('')
  const [rewriteLoading, setRewriteLoading] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [rewriteError, setRewriteError] = useState('')

  useEffect(() => {
    if (!script) fetchScript()
  }, [scriptId])

  // Close export menu on outside click
  useEffect(() => {
    if (!showExportMenu) return
    const close = () => setShowExportMenu(false)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [showExportMenu])

  async function fetchScript() {
    setLoading(true)
    try {
      const data = await api.getScript(scriptId)
      setScript(data)
      setCopyrightResult(data.copyright_risk)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCopyrightCheck() {
    setCheckingCopyright(true)
    try {
      const result = await api.checkCopyright(scriptId)
      setCopyrightResult(result)
    } catch (err) {
      console.error(err)
    } finally {
      setCheckingCopyright(false)
    }
  }

  async function handleRewrite() {
    if (!rewriteInstruction.trim() || !rewriteTarget) return
    setRewriteLoading(true)
    setRewriteError('')
    try {
      const res = await api.rewriteScript({
        script_id: scriptId,
        target: rewriteTarget.target,
        target_name: rewriteTarget.targetName,
        instruction: rewriteInstruction.trim(),
      })
      if (res.success) {
        // Update local script state
        setScript(prev => {
          const updated = { ...prev }
          if (rewriteTarget.target === 'overall') {
            Object.assign(updated, res.result)
          } else if (rewriteTarget.target === 'episode') {
            updated.episodes = (prev.episodes || []).map(ep =>
              ep.episode_number === parseInt(rewriteTarget.targetName) ? res.result : ep
            )
          } else if (rewriteTarget.target === 'character') {
            updated.characters = (prev.characters || []).map(c =>
              c.name === rewriteTarget.targetName ? res.result : c
            )
          } else if (rewriteTarget.target === 'scene') {
            updated.scenes = (prev.scenes || []).map(s =>
              s.name === rewriteTarget.targetName ? res.result : s
            )
          } else if (rewriteTarget.target === 'prop') {
            updated.props = (prev.props || []).map(p =>
              p.name === rewriteTarget.targetName ? res.result : p
            )
          }
          return updated
        })
        setRewriteTarget(null)
        setRewriteInstruction('')
      }
    } catch (err) {
      setRewriteError(err.message)
    } finally {
      setRewriteLoading(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><span className="spinner" style={{ width: 32, height: 32 }} /></div>
  }

  if (!script) {
    return (
      <div className="text-center py-20 text-ink-400">
        <p>剧本不存在</p>
        <Link to="/scripts" className="text-brand-600 text-sm mt-2 inline-block">返回列表</Link>
      </div>
    )
  }

  const currentEp = script.episodes?.find((ep) => ep.episode_number === activeEpisode)

  const tabs = [
    { key: 'episodes', label: '剧本', count: script.episodes?.length },
    { key: 'characters', label: '角色', count: script.characters?.length },
    { key: 'scenes', label: '场景', count: script.scenes?.length },
    { key: 'props', label: '道具', count: script.props?.length },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link to="/scripts" className="text-ink-400 hover:text-ink-600 text-sm no-underline">我的剧本</Link>
            <span className="text-ink-300">/</span>
          </div>
          <h1 className="text-2xl font-bold text-ink-900">{script.title}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className="badge badge-brand">{script.genre}</span>
            {script.style && <span className="badge badge-ink">{script.style}</span>}
            <span className="text-xs text-ink-400">{script.episodes?.length || 0}集</span>
            <span className="text-xs text-ink-400">{script.characters?.length || 0}个角色</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary text-sm" onClick={() => setRewriteTarget({ target: 'overall', targetName: '' })}>
            改写剧本
          </button>
          <button className="btn btn-secondary text-sm" onClick={handleCopyrightCheck} disabled={checkingCopyright}>
            {checkingCopyright ? '检测中...' : '版权检测'}
          </button>
          <div className="relative">
            <button className="btn btn-ghost text-sm" onClick={(e) => { e.stopPropagation(); setShowExportMenu(!showExportMenu) }}>导出</button>
            {showExportMenu && (
              <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border border-ink-100 py-1 z-50">
                <button className="w-full text-left px-4 py-2 text-sm text-ink-700 hover:bg-ink-50" onClick={() => { exportToMarkdown(script); setShowExportMenu(false) }}>
                  导出为 Markdown
                </button>
                <button className="w-full text-left px-4 py-2 text-sm text-ink-700 hover:bg-ink-50" onClick={() => { exportToDocx(script); setShowExportMenu(false) }}>
                  导出为 DOCX
                </button>
                <button className="w-full text-left px-4 py-2 text-sm text-ink-700 hover:bg-ink-50" onClick={() => { window.print(); setShowExportMenu(false) }}>
                  打印
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Synopsis */}
      {script.synopsis && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-2">剧情梗概</h2>
          <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-wrap">{script.synopsis}</p>
        </div>
      )}

      {/* Copyright Result */}
      {copyrightResult && <CopyrightCard result={copyrightResult} />}

      {/* Main Tabs */}
      <div className="border-b border-ink-100">
        <div className="flex gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-brand-500 text-brand-700'
                  : 'border-transparent text-ink-500 hover:text-ink-700'
              }`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
              {tab.count > 0 && <span className="ml-1 text-xs text-ink-400">({tab.count})</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'episodes' && (
        <EpisodesTab
          script={script}
          currentEp={currentEp}
          activeEpisode={activeEpisode}
          setActiveEpisode={setActiveEpisode}
          showAllShots={showAllShots}
          setShowAllShots={setShowAllShots}
          onRewrite={(epNum) => setRewriteTarget({ target: 'episode', targetName: String(epNum) })}
        />
      )}

      {activeTab === 'characters' && (
        <CharactersTab
          characters={script.characters || []}
          expandedChar={expandedChar}
          setExpandedChar={setExpandedChar}
          onRewrite={(name) => setRewriteTarget({ target: 'character', targetName: name })}
        />
      )}

      {activeTab === 'scenes' && (
        <ScenesTab
          scenes={script.scenes || []}
          onRewrite={(name) => setRewriteTarget({ target: 'scene', targetName: name })}
        />
      )}
      {activeTab === 'props' && (
        <PropsTab
          props={script.props || []}
          onRewrite={(name) => setRewriteTarget({ target: 'prop', targetName: name })}
        />
      )}

      {/* Rewrite Panel */}
      {rewriteTarget && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-end justify-center" onClick={() => setRewriteTarget(null)}>
          <div className="bg-white rounded-t-xl w-full max-w-2xl p-6 shadow-xl animate-fade-in" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-ink-900">
                改写{rewriteTarget.target === 'overall' ? '剧本整体' :
                     rewriteTarget.target === 'episode' ? `第${rewriteTarget.targetName}集` :
                     rewriteTarget.target === 'character' ? `角色「${rewriteTarget.targetName}」` :
                     rewriteTarget.target === 'scene' ? `场景「${rewriteTarget.targetName}」` :
                     `道具「${rewriteTarget.targetName}」`}
              </h3>
              <button className="text-ink-400 hover:text-ink-600" onClick={() => setRewriteTarget(null)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <textarea
              className="textarea mb-3"
              rows={3}
              placeholder="用自然语言描述你想要的修改，例如：把这个角色改成更冷酷的性格、增加一个反转剧情、让结尾更感人..."
              value={rewriteInstruction}
              onChange={(e) => setRewriteInstruction(e.target.value)}
              autoFocus
            />
            {rewriteError && <p className="text-sm text-red-600 mb-2">{rewriteError}</p>}
            <div className="flex justify-end gap-2">
              <button className="btn btn-ghost" onClick={() => setRewriteTarget(null)}>取消</button>
              <button className="btn btn-primary" onClick={handleRewrite} disabled={rewriteLoading || !rewriteInstruction.trim()}>
                {rewriteLoading ? (
                  <span className="flex items-center gap-2"><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> 改写中...</span>
                ) : '开始改写'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function CopyrightCard({ result }) {
  const colors = {
    low: { bg: 'bg-green-50', border: 'border-l-green-500', text: 'text-green-700', label: '低风险' },
    medium: { bg: 'bg-yellow-50', border: 'border-l-yellow-500', text: 'text-yellow-700', label: '中风险' },
    high: { bg: 'bg-red-50', border: 'border-l-red-500', text: 'text-red-700', label: '高风险' },
  }
  const c = colors[result.risk_level] || colors.low

  return (
    <div className={`card p-5 border-l-4 ${c.border}`}>
      <h2 className="text-sm font-semibold text-ink-900 mb-2">版权风险检测</h2>
      <div className="flex items-center gap-3 mb-3">
        <span className={`badge ${c.bg} ${c.text} border`}>{c.label}</span>
        <span className="text-sm text-ink-500">风险分数: {result.risk_score?.toFixed(1)}</span>
      </div>
      {result.suggestions?.length > 0 && (
        <ul className="text-sm text-ink-600 space-y-1">
          {result.suggestions.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}
    </div>
  )
}

function EpisodesTab({ script, currentEp, activeEpisode, setActiveEpisode, showAllShots, setShowAllShots, onRewrite }) {
  return (
    <div className="card">
      <div className="border-b border-ink-100 px-4 overflow-x-auto">
        <div className="flex gap-0 min-w-max">
          {script.episodes?.map((ep) => (
            <button
              key={ep.episode_number}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeEpisode === ep.episode_number
                  ? 'border-brand-500 text-brand-700'
                  : 'border-transparent text-ink-500 hover:text-ink-700'
              }`}
              onClick={() => setActiveEpisode(ep.episode_number)}
            >
              第{ep.episode_number}集
            </button>
          ))}
        </div>
      </div>

      {currentEp && (
        <div className="p-5 space-y-4 animate-fade-in">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-ink-900">第{currentEp.episode_number}集: {currentEp.title}</h2>
              {currentEp.summary && <p className="text-sm text-ink-600 mt-2">{currentEp.summary}</p>}
            </div>
            <button className="btn btn-ghost text-xs flex-shrink-0" onClick={() => onRewrite(currentEp.episode_number)}>
              改写本集
            </button>
          </div>

          <div className="flex flex-wrap gap-3">
            {currentEp.hook && (
              <div className="bg-ink-50 rounded-lg px-3 py-2 flex-1 min-w-[200px]">
                <div className="text-xs font-medium text-ink-500 mb-0.5">开头钩子</div>
                <p className="text-sm text-ink-800">{currentEp.hook}</p>
              </div>
            )}
            {currentEp.cliffhanger && (
              <div className="bg-brand-50 rounded-lg px-3 py-2 flex-1 min-w-[200px]">
                <div className="text-xs font-medium text-brand-600 mb-0.5">结尾悬念</div>
                <p className="text-sm text-ink-800">{currentEp.cliffhanger}</p>
              </div>
            )}
          </div>

          {currentEp.key_conflict && (
            <div className="text-sm text-ink-600">
              <span className="font-medium text-ink-700">核心冲突: </span>{currentEp.key_conflict}
            </div>
          )}

          {/* Shots */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-700">分镜脚本 ({currentEp.shots?.length || 0}个镜头)</h3>
              <button className="text-xs text-brand-600 hover:text-brand-700" onClick={() => setShowAllShots(!showAllShots)}>
                {showAllShots ? '收起' : '展开全部'}
              </button>
            </div>

            {currentEp.shots?.map((shot, i) => (
              <ShotCard key={i} shot={shot} showAll={showAllShots || i < 2} />
            ))}
          </div>

          {currentEp.total_duration > 0 && (
            <div className="text-right text-xs text-ink-400">总时长: {currentEp.total_duration}秒</div>
          )}
        </div>
      )}
    </div>
  )
}

function ShotCard({ shot, showAll }) {
  const [copied, setCopied] = useState(null)

  function copyText(text, label) {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 1500)
  }

  // Hook type config
  const hookConfig = {
    hook: { bg: 'bg-red-50', border: 'border-l-red-500', badge: 'bg-red-100 text-red-700', textBg: 'bg-red-100/60', label: '爆点钩子', icon: '!', desc: '黄金3秒，抓住观众注意力' },
    cliffhanger: { bg: 'bg-amber-50', border: 'border-l-amber-500', badge: 'bg-amber-100 text-amber-700', textBg: 'bg-amber-100/60', label: '结尾悬念', icon: '?', desc: '让人想看下一集' },
    foreshadowing: { bg: 'bg-purple-50', border: 'border-l-purple-500', badge: 'bg-purple-100 text-purple-700', textBg: 'bg-purple-100/60', label: '伏笔', icon: '*', desc: '后续会揭晓的线索' },
    turning_point: { bg: 'bg-blue-50', border: 'border-l-blue-500', badge: 'bg-blue-100 text-blue-700', textBg: 'bg-blue-100/60', label: '情节转折', icon: '~', desc: '剧情反转点' },
    emotional_peak: { bg: 'bg-pink-50', border: 'border-l-pink-500', badge: 'bg-pink-100 text-pink-700', textBg: 'bg-pink-100/60', label: '情感高潮', icon: '^', desc: '虐恋/甜宠/逆袭爽点' },
    revelation: { bg: 'bg-green-50', border: 'border-l-green-500', badge: 'bg-green-100 text-green-700', textBg: 'bg-green-100/60', label: '真相揭露', icon: '!', desc: '秘密曝光、身份揭示' },
    conflict: { bg: 'bg-orange-50', border: 'border-l-orange-500', badge: 'bg-orange-100 text-orange-700', textBg: 'bg-orange-100/60', label: '核心冲突', icon: '#', desc: '矛盾爆发' },
  }

  const hookType = shot.hook_type
  const hookInfo = hookConfig[hookType]
  const containerClass = hookInfo ? `${hookInfo.bg} border-l-4 ${hookInfo.border}` : 'border border-ink-100'
  const headerBg = hookInfo ? hookInfo.bg : 'bg-ink-50'

  const aiPrompt = shot.ai_prompt || shot.ai_prompt_cn

  return (
    <div className={`${containerClass} rounded-lg overflow-hidden`}>
      <div className={`${headerBg} px-4 py-2 flex items-center gap-3`}>
        <span className="text-xs font-bold text-ink-600">#{shot.shot_number}</span>
        <span className="badge badge-ink">{shot.shot_type}</span>
        <span className="badge badge-ink">{shot.camera_movement}</span>
        <span className="text-xs text-ink-400">{shot.duration}秒</span>
        {hookInfo && (
          <span className={`badge ${hookInfo.badge} font-semibold`}>{hookInfo.label}</span>
        )}
      </div>
      <div className="p-4 space-y-3">
        {/* Hook Detail Analysis - prominent display */}
        {hookInfo && shot.hook_detail && (
          <div className={`border-l-4 ${hookInfo.border} ${hookInfo.bg} rounded-r-sm p-3`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-sm font-bold ${hookInfo.badge}`}>{hookInfo.icon}</span>
              <span className="text-sm font-semibold text-ink-900">{hookInfo.label}</span>
              {hookInfo.desc && <span className="text-xs text-ink-400">({hookInfo.desc})</span>}
            </div>
            <p className="text-sm text-ink-700 leading-relaxed">{shot.hook_detail}</p>
          </div>
        )}

        <div>
          <div className="text-xs font-medium text-ink-500 mb-0.5">画面内容</div>
          <p className={`text-sm text-ink-800 ${hookInfo ? `inline ${hookInfo.textBg} px-1 rounded` : ''}`}>{shot.frame_content}</p>
        </div>
        {shot.dialogue && (
          <div>
            <div className="text-xs font-medium text-ink-500 mb-0.5">台词</div>
            <p className={`text-sm text-ink-800 italic ${hookInfo ? `inline ${hookInfo.textBg} px-1 rounded` : ''}`}>"{shot.dialogue}"</p>
          </div>
        )}
        {showAll && aiPrompt && (
          <div>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-xs font-medium text-ink-500">AI绘图提示词</span>
              <button className="text-xs text-brand-600" onClick={() => copyText(aiPrompt, 'prompt')}>
                {copied === 'prompt' ? '已复制' : '复制'}
              </button>
            </div>
            <p className="text-xs text-ink-600 bg-ink-50 p-2 rounded-lg font-mono">{aiPrompt}</p>
          </div>
        )}
        {showAll && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {shot.lighting && <div><span className="text-ink-400">光影:</span> {shot.lighting}</div>}
            {shot.emotion && <div><span className="text-ink-400">情绪:</span> {shot.emotion}</div>}
            {shot.sound_effects && <div><span className="text-ink-400">音效:</span> {shot.sound_effects}</div>}
            {shot.notes && <div><span className="text-ink-400">备注:</span> {shot.notes}</div>}
          </div>
        )}
      </div>
    </div>
  )
}

function CharactersTab({ characters, expandedChar, setExpandedChar, onRewrite }) {
  if (!characters.length) return <div className="text-center py-12 text-ink-400">暂无角色数据</div>

  return (
    <div className="space-y-4">
      {characters.map((char, i) => (
        <div key={i} className="card overflow-hidden">
          <div
            className="p-4 cursor-pointer hover:bg-ink-50 transition-colors"
            onClick={() => setExpandedChar(expandedChar === i ? null : i)}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-ink-900">{char.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  {char.identity && <span className="badge badge-brand">{char.identity}</span>}
                  {char.age && <span className="text-xs text-ink-400">{char.age}</span>}
                </div>
                {char.personality && <p className="text-xs text-ink-500 mt-1">性格: {char.personality}</p>}
              </div>
              <div className="flex items-center gap-2">
                <button className="text-xs text-brand-600 hover:text-brand-700" onClick={(e) => { e.stopPropagation(); onRewrite(char.name) }}>
                  改写
                </button>
                <svg className={`w-5 h-5 text-ink-400 transition-transform ${expandedChar === i ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {expandedChar === i && (
            <div className="border-t border-ink-100 p-4 space-y-3 animate-fade-in">
              {char.appearance && (
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-0.5">外貌描述</div>
                  <p className="text-sm text-ink-800">{char.appearance}</p>
                </div>
              )}
              {char.clothing && (
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-0.5">穿着</div>
                  <p className="text-sm text-ink-800">{char.clothing}</p>
                </div>
              )}
              {char.arc && (
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-0.5">角色弧线</div>
                  <p className="text-sm text-ink-800">{char.arc}</p>
                </div>
              )}

              {/* AI Prompts */}
              {(char.ai_prompt || char.three_view_prompt) && (
                <PromptBlock label="三视图AI提示词" text={char.ai_prompt || char.three_view_prompt} id={`char_${i}`} />
              )}

              {/* Expression Prompts */}
              {char.expression_prompts && Object.keys(char.expression_prompts).length > 0 && (
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-2">表情提示词</div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(char.expression_prompts).map(([expr, prompts]) => (
                      <div key={expr} className="bg-ink-50 rounded-lg p-2">
                        <div className="text-xs font-bold text-ink-600 mb-0.5">{expr}</div>
                        {typeof prompts === 'object' ? (
                          <p className="text-xs text-ink-600 font-mono truncate">{prompts.cn || Object.values(prompts)[0]}</p>
                        ) : (
                          <p className="text-xs text-ink-600 font-mono truncate">{prompts}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ScenesTab({ scenes, onRewrite }) {
  if (!scenes.length) return <div className="text-center py-12 text-ink-400">暂无场景数据</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {scenes.map((scene, i) => (
        <div key={i} className="card p-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-ink-900">{scene.name}</h3>
            <button className="text-xs text-brand-600 hover:text-brand-700" onClick={() => onRewrite(scene.name)}>改写</button>
          </div>
          <p className="text-xs text-ink-600 mb-2">{scene.description}</p>
          {scene.atmosphere && <p className="text-xs text-ink-400 mb-2">氛围: {scene.atmosphere}</p>}
          {(scene.scene_prompt) && (
            <PromptBlock label="场景AI提示词" text={scene.scene_prompt} id={`scene_${i}`} />
          )}
          {scene.scene_variants && (
            <div className="mt-2">
              <div className="text-xs font-medium text-ink-500 mb-1">变体</div>
              <div className="flex flex-wrap gap-1">
                {Object.keys(scene.scene_variants).map(v => (
                  <span key={v} className="badge badge-ink">{v}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function PropsTab({ props, onRewrite }) {
  if (!props.length) return <div className="text-center py-12 text-ink-400">暂无道具数据</div>

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {props.map((prop, i) => (
        <div key={i} className="card p-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-ink-900">{prop.name}</h3>
            <button className="text-xs text-brand-600 hover:text-brand-700" onClick={() => onRewrite(prop.name)}>改写</button>
          </div>
          <p className="text-xs text-ink-600 mb-2">{prop.description}</p>
          {(prop.prop_prompt) && (
            <PromptBlock label="道具AI提示词" text={prop.prop_prompt} id={`prop_${i}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function PromptBlock({ label, text, id }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-xs font-medium text-ink-500">{label}</span>
        <button className="text-xs text-brand-600" onClick={copy}>{copied ? '已复制' : '复制'}</button>
      </div>
      <p className="text-xs text-ink-600 bg-ink-50 p-2 rounded-lg font-mono break-all">{text}</p>
    </div>
  )
}
