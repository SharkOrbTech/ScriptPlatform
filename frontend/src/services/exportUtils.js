import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'

function buildMarkdown(script) {
  const lines = []
  lines.push(`# ${script.title}`)
  lines.push('')
  lines.push(`**题材**: ${script.genre} | **风格**: ${script.style || '-'} | **目标受众**: ${script.target_audience || '-'}`)
  lines.push('')

  if (script.logline) {
    lines.push(`> ${script.logline}`)
    lines.push('')
  }

  if (script.synopsis) {
    lines.push('## 剧情梗概')
    lines.push('')
    lines.push(script.synopsis)
    lines.push('')
  }

  if (script.theme) {
    lines.push(`**核心主题**: ${script.theme}`)
  }
  if (script.emotional_tone) {
    lines.push(`**情感基调**: ${script.emotional_tone}`)
  }
  if (script.theme || script.emotional_tone) lines.push('')

  // Characters
  if (script.characters?.length > 0) {
    lines.push('## 角色')
    lines.push('')
    for (const c of script.characters) {
      lines.push(`### ${c.name}`)
      if (c.age) lines.push(`- **年龄**: ${c.age}`)
      if (c.identity) lines.push(`- **身份**: ${c.identity}`)
      if (c.personality) lines.push(`- **性格**: ${c.personality}`)
      if (c.appearance) lines.push(`- **外貌**: ${c.appearance}`)
      if (c.clothing) lines.push(`- **穿着**: ${c.clothing}`)
      if (c.signature_element) lines.push(`- **标志元素**: ${c.signature_element}`)
      if (c.arc) lines.push(`- **成长弧线**: ${c.arc}`)
      lines.push('')
    }
  }

  // Episodes
  if (script.episodes?.length > 0) {
    lines.push('## 分集剧本')
    lines.push('')
    for (const ep of script.episodes) {
      lines.push(`### 第${ep.episode_number}集: ${ep.title}`)
      lines.push('')
      if (ep.summary) {
        lines.push(`**概要**: ${ep.summary}`)
        lines.push('')
      }
      if (ep.hook) lines.push(`**开头钩子**: ${ep.hook}`)
      if (ep.cliffhanger) lines.push(`**结尾悬念**: ${ep.cliffhanger}`)
      if (ep.key_conflict) lines.push(`**核心冲突**: ${ep.key_conflict}`)
      if (ep.emotional_arc) lines.push(`**情感弧线**: ${ep.emotional_arc}`)
      if (ep.hook || ep.cliffhanger || ep.key_conflict || ep.emotional_arc) lines.push('')

      if (ep.shots?.length > 0) {
        lines.push('#### 分镜脚本')
        lines.push('')
        for (const shot of ep.shots) {
          lines.push(`**镜头 ${shot.shot_number}** [${shot.shot_type || '-'}] [${shot.camera_movement || '-'}]`)
          if (shot.frame_content) lines.push(`画面: ${shot.frame_content}`)
          if (shot.narration) lines.push(`旁白: ${shot.narration}`)
          if (shot.dialogue) lines.push(`台词: ${shot.dialogue}`)
          if (shot.video_prompt) lines.push(`视频生成提示词: ${shot.video_prompt}`)
          else if (shot.ai_prompt) lines.push(`AI提示词: ${shot.ai_prompt}`)
          if (shot.hook_type) lines.push(`钩子类型: ${shot.hook_type} - ${shot.hook_detail || ''}`)
          lines.push('')
        }
      }
    }
  }

  // Scenes
  const scenes = script.scenes || script_data?.scenes || []
  if (scenes.length > 0) {
    lines.push('## 场景')
    lines.push('')
    for (const s of scenes) {
      lines.push(`### ${s.name}`)
      if (s.description) lines.push(s.description)
      if (s.atmosphere) lines.push(`氛围: ${s.atmosphere}`)
      lines.push('')
    }
  }

  // Props
  const props = script.props || script_data?.props || []
  if (props.length > 0) {
    lines.push('## 道具')
    lines.push('')
    for (const p of props) {
      lines.push(`- **${p.name}**: ${p.description || ''}`)
    }
    lines.push('')
  }

  return lines.join('\n')
}

export function exportToMarkdown(script) {
  const md = buildMarkdown(script)
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${script.title || '剧本'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

export function exportToDocx(script) {
  const children = []

  // Title
  children.push(new Paragraph({
    children: [new TextRun({ text: script.title || '剧本', bold: true, size: 36 })],
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
  }))

  // Meta
  children.push(new Paragraph({
    children: [new TextRun({ text: `题材: ${script.genre}  |  风格: ${script.style || '-'}  |  目标受众: ${script.target_audience || '-'}`, size: 22, color: '666666' })],
    alignment: AlignmentType.CENTER,
  }))
  children.push(new Paragraph({ text: '' }))

  if (script.logline) {
    children.push(new Paragraph({
      children: [new TextRun({ text: script.logline, italics: true, size: 24 })],
    }))
    children.push(new Paragraph({ text: '' }))
  }

  if (script.synopsis) {
    children.push(new Paragraph({
      children: [new TextRun({ text: '剧情梗概', bold: true, size: 28 })],
      heading: HeadingLevel.HEADING_2,
    }))
    children.push(new Paragraph({
      children: [new TextRun({ text: script.synopsis, size: 22 })],
    }))
    children.push(new Paragraph({ text: '' }))
  }

  // Characters
  if (script.characters?.length > 0) {
    children.push(new Paragraph({
      children: [new TextRun({ text: '角色', bold: true, size: 28 })],
      heading: HeadingLevel.HEADING_2,
    }))
    for (const c of script.characters) {
      children.push(new Paragraph({
        children: [new TextRun({ text: c.name, bold: true, size: 24 })],
        heading: HeadingLevel.HEADING_3,
      }))
      const fields = [
        ['年龄', c.age], ['身份', c.identity], ['性格', c.personality],
        ['外貌', c.appearance], ['穿着', c.clothing], ['标志元素', c.signature_element],
      ]
      for (const [label, val] of fields) {
        if (val) {
          children.push(new Paragraph({
            children: [
              new TextRun({ text: `${label}: `, bold: true, size: 22 }),
              new TextRun({ text: val, size: 22 }),
            ],
          }))
        }
      }
      children.push(new Paragraph({ text: '' }))
    }
  }

  // Episodes
  if (script.episodes?.length > 0) {
    children.push(new Paragraph({
      children: [new TextRun({ text: '分集剧本', bold: true, size: 28 })],
      heading: HeadingLevel.HEADING_2,
    }))
    for (const ep of script.episodes) {
      children.push(new Paragraph({
        children: [new TextRun({ text: `第${ep.episode_number}集: ${ep.title}`, bold: true, size: 24 })],
        heading: HeadingLevel.HEADING_3,
      }))
      if (ep.summary) {
        children.push(new Paragraph({
          children: [new TextRun({ text: `概要: ${ep.summary}`, size: 22 })],
        }))
      }
      if (ep.hook) {
        children.push(new Paragraph({
          children: [
            new TextRun({ text: '开头钩子: ', bold: true, size: 22 }),
            new TextRun({ text: ep.hook, size: 22 }),
          ],
        }))
      }
      if (ep.cliffhanger) {
        children.push(new Paragraph({
          children: [
            new TextRun({ text: '结尾悬念: ', bold: true, size: 22 }),
            new TextRun({ text: ep.cliffhanger, size: 22 }),
          ],
        }))
      }
      children.push(new Paragraph({ text: '' }))

      if (ep.shots?.length > 0) {
        for (const shot of ep.shots) {
          children.push(new Paragraph({
            children: [
              new TextRun({ text: `镜头 ${shot.shot_number}`, bold: true, size: 22 }),
              new TextRun({ text: ` [${shot.shot_type || '-'}] [${shot.camera_movement || '-'}]`, size: 22, color: '888888' }),
            ],
          }))
          if (shot.frame_content) {
            children.push(new Paragraph({
              children: [new TextRun({ text: `画面: ${shot.frame_content}`, size: 22 })],
            }))
          }
          if (shot.narration) {
            children.push(new Paragraph({
              children: [new TextRun({ text: `旁白: ${shot.narration}`, size: 22, italics: true, color: '666666' })],
            }))
          }
          if (shot.dialogue) {
            children.push(new Paragraph({
              children: [new TextRun({ text: `台词: ${shot.dialogue}`, size: 22 })],
            }))
          }
          if (shot.video_prompt) {
            children.push(new Paragraph({
              children: [new TextRun({ text: `视频生成提示词: ${shot.video_prompt}`, size: 20, italics: true, color: '555555' })],
            }))
          } else if (shot.ai_prompt) {
            children.push(new Paragraph({
              children: [new TextRun({ text: `AI提示词: ${shot.ai_prompt}`, size: 20, italics: true, color: '555555' })],
            }))
          }
          children.push(new Paragraph({ text: '' }))
        }
      }
    }
  }

  const doc = new Document({
    sections: [{ children }],
  })

  Packer.toBlob(doc).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${script.title || '剧本'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  })
}

// ============================================================
// Helper: build markdown for each section
// ============================================================

function buildOverviewMarkdown(script) {
  const lines = []
  lines.push(`# ${script.title}`)
  lines.push('')
  lines.push(`**题材**: ${script.genre} | **风格**: ${script.style || '-'} | **目标受众**: ${script.target_audience || '-'}`)
  lines.push('')
  if (script.logline) { lines.push(`> ${script.logline}`); lines.push('') }
  if (script.theme) lines.push(`**核心主题**: ${script.theme}`)
  if (script.emotional_tone) lines.push(`**情感基调**: ${script.emotional_tone}`)
  if (script.theme || script.emotional_tone) lines.push('')
  if (script.synopsis) { lines.push('## 剧情梗概'); lines.push(''); lines.push(script.synopsis); lines.push('') }
  return lines.join('\n')
}

function buildCharactersMarkdown(script) {
  const lines = []
  lines.push('# 角色设定')
  lines.push('')
  for (const c of script.characters || []) {
    lines.push(`## ${c.name}`)
    if (c.age) lines.push(`- **年龄**: ${c.age}`)
    if (c.identity) lines.push(`- **身份**: ${c.identity}`)
    if (c.personality) lines.push(`- **性格**: ${c.personality}`)
    if (c.appearance) lines.push(`- **外貌**: ${c.appearance}`)
    if (c.clothing) lines.push(`- **穿着**: ${c.clothing}`)
    if (c.signature_element) lines.push(`- **标志元素**: ${c.signature_element}`)
    if (c.arc) lines.push(`- **成长弧线**: ${c.arc}`)
    if (c.three_view_prompt) lines.push(`- **三视图提示词**: ${c.three_view_prompt}`)
    else if (c.ai_prompt) lines.push(`- **AI提示词**: ${c.ai_prompt}`)
    lines.push('')
  }
  return lines.join('\n')
}

function buildEpisodesMarkdown(script) {
  const lines = []
  lines.push('# 分集剧本')
  lines.push('')
  for (const ep of script.episodes || []) {
    lines.push(`## 第${ep.episode_number}集: ${ep.title}`)
    lines.push('')
    if (ep.summary) { lines.push(`**概要**: ${ep.summary}`); lines.push('') }
    if (ep.hook) lines.push(`**开头钩子**: ${ep.hook}`)
    if (ep.cliffhanger) lines.push(`**结尾悬念**: ${ep.cliffhanger}`)
    if (ep.key_conflict) lines.push(`**核心冲突**: ${ep.key_conflict}`)
    if (ep.emotional_arc) lines.push(`**情感弧线**: ${ep.emotional_arc}`)
    if (ep.hook || ep.cliffhanger || ep.key_conflict || ep.emotional_arc) lines.push('')

    if (ep.shots?.length > 0) {
      lines.push('### 分镜脚本')
      lines.push('')
      for (const shot of ep.shots) {
        lines.push(`**镜头 ${shot.shot_number}** [${shot.shot_type || '-'}] [${shot.camera_movement || '-'}]`)
        if (shot.frame_content) lines.push(`画面: ${shot.frame_content}`)
        if (shot.dialogue) lines.push(`台词: ${shot.dialogue}`)
        if (shot.video_prompt) lines.push(`视频生成提示词: ${shot.video_prompt}`)
        else if (shot.ai_prompt) lines.push(`AI提示词: ${shot.ai_prompt}`)
        if (shot.hook_type) lines.push(`钩子: ${shot.hook_type} - ${shot.hook_detail || ''}`)
        lines.push('')
      }
    }
  }
  return lines.join('\n')
}

function buildScenesMarkdown(script) {
  const lines = []
  lines.push('# 场景设定')
  lines.push('')
  const scenes = script.scenes || []
  for (const s of scenes) {
    lines.push(`## ${s.name}`)
    if (s.description) lines.push(s.description)
    if (s.atmosphere) lines.push(`**氛围**: ${s.atmosphere}`)
    if (s.scene_prompt) lines.push(`**AI提示词**: ${s.scene_prompt}`)
    lines.push('')
  }
  return lines.join('\n')
}

function buildPropsMarkdown(script) {
  const lines = []
  lines.push('# 道具设定')
  lines.push('')
  const props = script.props || []
  for (const p of props) {
    lines.push(`## ${p.name}`)
    if (p.description) lines.push(p.description)
    if (p.significance) lines.push(`**剧情意义**: ${p.significance}`)
    if (p.appearance) lines.push(`**外观**: ${p.appearance}`)
    if (p.ai_prompt) lines.push(`**AI提示词**: ${p.ai_prompt}`)
    lines.push('')
  }
  return lines.join('\n')
}

// Helper: build a simple DOCX blob for a section
function buildSimpleDocx(title, markdownContent) {
  const children = []
  children.push(new Paragraph({
    children: [new TextRun({ text: title, bold: true, size: 36 })],
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
  }))
  children.push(new Paragraph({ text: '' }))

  // Parse markdown into paragraphs (simple approach)
  for (const line of markdownContent.split('\n')) {
    if (line.startsWith('# ')) {
      children.push(new Paragraph({
        children: [new TextRun({ text: line.replace(/^#+\s*/, ''), bold: true, size: 32 })],
        heading: HeadingLevel.HEADING_1,
      }))
    } else if (line.startsWith('## ')) {
      children.push(new Paragraph({
        children: [new TextRun({ text: line.replace(/^#+\s*/, ''), bold: true, size: 28 })],
        heading: HeadingLevel.HEADING_2,
      }))
    } else if (line.startsWith('### ')) {
      children.push(new Paragraph({
        children: [new TextRun({ text: line.replace(/^#+\s*/, ''), bold: true, size: 24 })],
        heading: HeadingLevel.HEADING_3,
      }))
    } else if (line.includes('**')) {
      const parts = line.split(/(\*\*[^*]+\*\*)/)
      const runs = parts.map(part => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return new TextRun({ text: part.slice(2, -2), bold: true, size: 22 })
        }
        return new TextRun({ text: part, size: 22 })
      })
      children.push(new Paragraph({ children: runs }))
    } else if (line.startsWith('> ')) {
      children.push(new Paragraph({
        children: [new TextRun({ text: line.replace(/^>\s*/, ''), italics: true, size: 22, color: '666666' })],
      }))
    } else if (line.trim()) {
      children.push(new Paragraph({
        children: [new TextRun({ text: line, size: 22 })],
      }))
    } else {
      children.push(new Paragraph({ text: '' }))
    }
  }

  const doc = new Document({ sections: [{ children }] })
  return Packer.toBlob(doc)
}

// ============================================================
// ZIP Export
// ============================================================

export async function exportToZip(script, format = 'md') {
  const zip = new JSZip()
  const title = script.title || '剧本'
  const folder = zip.folder(title)

  if (format === 'md' || format === 'both') {
    folder.file('01_剧本概述.md', buildOverviewMarkdown(script))
    folder.file('02_角色设定.md', buildCharactersMarkdown(script))
    folder.file('03_分集剧本.md', buildEpisodesMarkdown(script))
    folder.file('04_场景设定.md', buildScenesMarkdown(script))
    folder.file('05_道具设定.md', buildPropsMarkdown(script))
  }

  if (format === 'docx' || format === 'both') {
    const overviewBlob = await buildSimpleDocx(`${title} - 剧本概述`, buildOverviewMarkdown(script))
    folder.file('01_剧本概述.docx', overviewBlob)

    const charsBlob = await buildSimpleDocx(`${title} - 角色设定`, buildCharactersMarkdown(script))
    folder.file('02_角色设定.docx', charsBlob)

    const epsBlob = await buildSimpleDocx(`${title} - 分集剧本`, buildEpisodesMarkdown(script))
    folder.file('03_分集剧本.docx', epsBlob)

    const scenesBlob = await buildSimpleDocx(`${title} - 场景设定`, buildScenesMarkdown(script))
    folder.file('04_场景设定.docx', scenesBlob)

    const propsBlob = await buildSimpleDocx(`${title} - 道具设定`, buildPropsMarkdown(script))
    folder.file('05_道具设定.docx', propsBlob)
  }

  const zipBlob = await zip.generateAsync({ type: 'blob' })
  saveAs(zipBlob, `${title}.zip`)
}
