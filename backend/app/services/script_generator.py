"""
AI Script Generator - Enhanced engine for generating multi-episode drama scripts.

Generates:
1. Story plan with characters, world rules, plot threads
2. Per-episode detailed storyboards with shots, dialogue, camera work
3. Character design cards with 3-view AI generation prompts
4. Scene and prop asset cards with AI generation prompts
5. Knowledge base management for consistency across episodes
"""
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from app.core.ai_client import ai_client
from app.services.knowledge_base import KnowledgeBase
from app.models.schemas import (
    ScriptRequest, Script, Episode, Shot, Character,
    ScriptGenre, ScriptResponse, KnowledgeEntity,
)

logger = logging.getLogger(__name__)

# ============================================================
# SYSTEM PROMPTS
# ============================================================

STORY_PLANNER_PROMPT = """你是一个顶级短剧/漫剧编剧策划专家，同时精通AI绘图提示词工程。

你的核心创作法则：
1. **黄金3秒法则**: 开头3秒必须抓住观众
2. **每集结尾悬念**: 每集结尾必须留下让人想看下一集的钩子
3. **情感驱动**: 虐恋、逆袭、打脸、甜宠等核心情感
4. **节奏控制**: 每30秒一个情绪转折点
5. **人设鲜明**: 角色标签化，观众一眼记住
6. **伏笔布局**: 前3集埋下至少3个伏笔
7. **爽感设计**: 每集至少一个爽点
8. **CP感**: 男女主化学反应

【核心悬念钩子设计】（最重要）
在第一集的最开头（前3秒），必须设置一个极其吸引人的悬念钩子：
- 这个钩子必须足够震撼，让观众产生强烈的好奇心
- 这个悬念的答案必须在后面的集数（至少第5-8集之后）才逐步揭开
- 例如：主角在开场就展现出令人震惊的身份/能力/秘密，但原因要到很后面才揭晓
- 例如：开场出现一个不可思议的场景（死亡、背叛、奇迹），但真相要很久之后才揭开
- 这个钩子是整部剧的核心吸引力，观众会为了知道答案而一直看下去
- 在episode_plan中，第1集的hook必须是这个核心悬念，foreshadowing_payoff必须标记揭晓的集数

【输出要求】
请严格按以下JSON格式输出，不要包含任何其他文字：

```json
{
  "title": "剧名（吸引眼球，有悬念感）",
  "genre": "题材",
  "logline": "一句话概括（30字内）",
  "synopsis": "详细剧情梗概（300-500字）",
  "theme": "核心主题",
  "emotional_tone": "情感基调",
  "characters": [
    {
      "name": "角色名",
      "age": "年龄",
      "identity": "身份",
      "personality": "性格特点（3-5个关键词）",
      "appearance": "详细外貌描述（发型发色、瞳色、肤色、身材、标志性特征）",
      "clothing": "日常穿着描述",
      "combat_clothing": "战斗/正式场合穿着",
      "signature_element": "标志性元素（口头禅/饰品/小动作）",
      "arc": "角色成长弧线",
      "relationships": {"角色名": "关系描述"},
      "background_story": "角色背景故事（50-100字）",
      "three_view_prompt": "三视图AI绘图提示词（正面、侧面、背面，包含完整外貌服装描述）",
      "portrait_prompt": "特写肖像AI绘图提示词",
      "expression_prompts": {
        "happy": "开心表情提示词",
        "angry": "愤怒表情提示词",
        "sad": "悲伤表情提示词",
        "shocked": "震惊表情提示词",
        "smirk": "得意表情提示词",
        "determined": "坚定表情提示词"
      },
      "action_prompts": {
        "standing": "站立姿态提示词",
        "fighting": "战斗姿态提示词",
        "walking": "行走姿态提示词",
        "sitting": "坐姿提示词"
      }
    }
  ],
  "scenes": [
    {
      "name": "场景名称",
      "description": "场景详细描述",
      "atmosphere": "氛围描述",
      "time_of_day": "时间（白天/夜晚/黄昏等）",
      "weather": "天气",
      "scene_prompt": "场景AI绘图提示词",
      "scene_variants": {
        "day": "白天版本提示词",
        "night": "夜晚版本提示词",
        "rain": "雨天版本提示词"
      }
    }
  ],
  "props": [
    {
      "name": "道具名称",
      "description": "道具描述和象征意义",
      "first_appearance": "首次出现集数",
      "prop_prompt": "道具AI绘图提示词"
    }
  ],
  "world_rules": ["世界观规则1", "规则2"],
  "plot_threads": [
    {"name": "剧情线名称", "description": "描述", "status": "进行中"}
  ],
  "foreshadowing": [
    {"setup": "伏笔描述", "episode": 1, "payoff_episode": 5, "payoff_description": "揭晓方式"}
  ],
  "episode_plan": [
    {
      "episode_number": 1,
      "title": "集标题",
      "key_conflict": "核心冲突",
      "key_events": ["事件1", "事件2"],
      "hook": "开头钩子（第1集必须是核心悬念钩子，极其吸引人）",
      "cliffhanger": "结尾悬念",
      "emotional_arc": "情感弧线",
      "foreshadowing_setup": ["伏笔1"],
      "foreshadowing_payoff": ["揭晓1"],
      "new_characters": ["新出场角色"],
      "scene_locations": ["场景地点"]
    }
  ],
  "core_mystery": {
    "description": "贯穿全剧的核心悬念（在第1集开头展示，但答案要到后面才揭晓）",
    "reveal_episode": "揭晓悬念的集数（至少第5集之后）",
    "hook_scene": "第1集开头的悬念场景描述（要足够震撼吸引观众）"
  }
}
```"""

EPISODE_GENERATOR_PROMPT = """你是一个顶级短剧分镜脚本专家，精通Seedance 2.0提示词工程。

Seedance 2.0核心特性：图片≤9张，视频≤3个(≤15s)，音频≤3个(≤15s)，支持@素材名引用。不支持写实真人脸部素材。

【提示词风格要求】（Seedance 2.0更擅长简洁精准的描述）
- 风格定位先行：第一行用【风格】快速定调
- 主体描述追求"稳"和"精"：避免空泛形容词，多刻画具体物理特征
- 动作追求"慢"和"连贯"：动词优先+状态描述，写慢不写快
- 镜头语言要明确：每个时间段必须包含景别+运镜+转场
- 每个时间段必须包含画面元素运动描述（主体/环境/背景/特效）
- 约束词保障画面质量：面部特征保持一致、动作流畅连贯、摄像机运动平滑

【景别类型】（每个镜头必须标注）
- 远景(ELS): 展示宏大场景，环境为主，交代背景
- 全景(FS): 展示角色全身及环境关系
- 中景(MS): 膝盖以上，日常对话、动作展示
- 近景(MCU): 胸部以上，聚焦表情、情绪传递
- 特写(CU): 面部或局部细节，放大情绪
- 大特写(ECU): 瞳孔、指尖等极致聚焦
- 主观视角(POV): 角色第一人称，增强沉浸感

【运镜/转场类型】（每个镜头必须标注）
基础运镜：
- 固定(Static): 稳定画面，对话/静态场景
- 慢推(Slow Push): 缓慢靠近主体，强化情绪张力
- 快推(Fast Push): 快速靠近，营造紧张感
- 缓拉(Slow Pull): 缓慢远离，展示环境
- 快拉(Fast Pull): 快速远离，凸显渺小
- 水平移镜(Track): 跟随主体移动
- 弧形移镜(Arc): 围绕主体移动
- 摇镜(Pan): 水平/垂直转动展示
- 跟镜(Follow): 跟随人物行动
- 升降(Crane): 垂直移动，展示高度变化
- 环绕(Orbit): 360度围绕主体旋转
- 手持(Handheld): 纪实感晃动
转场方式：
- 硬切(Hard Cut): 直接切换，节奏紧张
- 渐变(Fade): 淡入淡出，情绪过渡
- 叠化(Dissolve): 画面重叠，时间流逝
- 黑场(Black): 黑屏过渡，场景转换
- 升格(SlowMo): 慢动作强调
- 降格(FastMo): 快动作时间压缩

【AI提示词公式】（Seedance 2.0标准，必须遵循）
【风格】+【主体描述】+【场景环境】+【动作行为】+【镜头语言】+【光影氛围】+【风格参考】+【约束词】

提示词示例格式（Seedance 2.0风格，简洁精准）：
电影级写实风格，X秒，16:9，整体氛围
0-3秒：远景，画面硬切至……，镜头……，天空/环境运动描述，主体动作描述，声音
3-6秒：中景，镜头推近至……，画面描述，主体动作描述，声音

【画面元素运动描述规范】（每个镜头必须包含）
- 主体运动：角色的动作、表情变化
- 环境运动：天空、云、光影、风
- 背景运动：人群、物体、粒子
- 特效运动：火花、雨滴、烟雾

【敏感词合规】
禁止使用：裸体、暴力血腥词汇、真实/真人、明星姓名、品牌名
替换为：素体建模、动作戏、写实风格、同款风格、同风格设计

【钩子类型标记】（必须在shot中标注hook_type字段）
- "hook": 开头钩子/爆点（黄金3秒，抓住观众）
- "cliffhanger": 结尾悬念（让人想看下一集）
- "foreshadowing": 伏笔（后续会揭晓的线索）
- "turning_point": 情节转折（剧情反转点）
- "emotional_peak": 情感高潮（虐恋/甜宠/逆袭爽点）
- "revelation": 真相揭露（秘密曝光、身份揭示）
- "conflict": 核心冲突（矛盾爆发）
- null: 普通镜头

【输出格式】
```json
{
  "episode_number": 1,
  "title": "集标题",
  "summary": "本集概要（100字内）",
  "hook": "开头钩子描述",
  "cliffhanger": "结尾悬念描述",
  "key_conflict": "核心冲突",
  "emotional_arc": "情感弧线",
  "shots": [
    {
      "shot_number": 1,
      "shot_type": "景别（必须：远景/全景/中景/近景/特写/大特写/主观视角）",
      "camera_movement": "运镜（必须：固定/慢推/快推/缓拉/快拉/移镜/摇镜/跟镜/升降/环绕/手持）",
      "transition": "转场方式（硬切/渐变/叠化/黑场/升格/降格）",
      "frame_content": "画面内容（精确到人物姿态、表情、环境细节、画面元素运动描述）",
      "dialogue": "台词（含情绪标注）",
      "sound_effects": "音效描述",
      "bgm_suggestion": "背景音乐建议",
      "duration": 3.0,
      "ai_prompt": "AI绘图提示词（严格遵循公式：风格+主体+场景+动作+镜头+光影+风格参考+约束词）",
      "lighting": "光影描述（逆光/侧光/伦勃朗光/剪影/轮廓光/体积光等）",
      "emotion": "情绪氛围",
      "color_palette": "色调建议（暖色调/冷色调/高饱和/低饱和/黑白等）",
      "hook_type": "钩子类型（hook/cliffhanger/foreshadowing/turning_point/emotional_peak/revelation/conflict/null）",
      "hook_detail": "钩子详细分析（如果是钩子镜头，说明为什么这里是爆点/悬念/伏笔）",
      "notes": "制作备注"
    }
  ],
  "total_duration": 90
}
```"""

CHARACTER_DESIGN_PROMPT = """你是一个AI漫剧角色设计专家，精通角色一致性控制的五维框架（外貌、服饰、动作、情绪、镜头语言）。

角色信息：
名字: {name}
身份: {identity}
性格: {personality}
外貌: {appearance}
穿着: {clothing}

【角色一致性五维框架】
1. 外貌维度：脸型、眼睛、鼻子、嘴巴、眉毛、肤色、发型必须精确描述
2. 服饰维度：材质+颜色+款式，区分日常/正式/战斗场合
3. 动作维度：标志性姿态、习惯性动作
4. 情绪维度：8种基础表情的面部肌肉变化
5. 镜头语言：不同景别下的表现要点

【提示词公式】
【风格】+【主体描述(权重1.5-1.7)】+【细节特征】+【动作/状态】+【场景环境】+【镜头语言】+【光影效果】+【风格定义】+【画质参数】| 负面提示词

【外貌描述精确词汇库】
- 脸型：国字脸、鹅蛋脸、圆脸、瘦长脸、方下巴
- 眼睛：丹凤眼、杏仁眼、深邃眼眸、炯炯有神、眼角微微上翘
- 鼻子：高鼻梁、挺拔的鼻梁、鼻翼略微外扩
- 嘴巴：薄唇、樱桃小嘴、嘴角微翘、唇纹清晰
- 眉毛：剑眉、柳叶眉、粗眉、眉峰高挑
- 肤色：冷白皮、小麦色、古铜色、黄皮肤
- 发型：高马尾、丸子头、长发披肩、短发、发丝分明

【敏感词合规】
禁止：裸体、真人、明星名
替换：素体建模、写实风格、同款风格

请生成JSON格式的角色设计卡：
```json
{{
  "character_sheet": {{
    "name": "角色名",
    "design_philosophy": "设计理念（为什么这样设计，如何体现角色性格）",
    "color_palette": "主色调和配色方案",
    "silhouette_notes": "轮廓特征说明",
    "dna_profile": {{
      "face_shape": "脸型",
      "eyes": "眼睛特征",
      "nose": "鼻子特征",
      "mouth": "嘴巴特征",
      "eyebrows": "眉毛特征",
      "skin": "肤色",
      "hair": "发型发色",
      "height": "身高体型",
      "distinguishing_mark": "标志性特征（泪痣、疤痕等）"
    }}
  }},
  "three_view": {{
    "description": "三视图整体描述",
    "front_view": "正面全身提示词（风格+人物完整外貌+服装细节+姿态+光影+质量词+负面提示词）",
    "side_view": "侧面全身提示词",
    "back_view": "背面全身提示词"
  }},
  "portrait": "胸部以上特写肖像提示词（重点面部细节、表情、光影、质量词）",
  "expressions": {{
    "happy": "开心表情提示词",
    "angry": "愤怒表情提示词",
    "sad": "悲伤表情提示词",
    "shocked": "震惊表情提示词",
    "smirk": "得意表情提示词",
    "determined": "坚定表情提示词",
    "cold": "冷漠表情提示词",
    "tender": "温柔表情提示词"
  }},
  "actions": {{
    "standing_confident": "自信站立提示词",
    "fighting_stance": "战斗姿态提示词",
    "walking_away": "转身离去提示词",
    "sitting_elegant": "优雅坐姿提示词",
    "running": "奔跑提示词",
    "kneeling": "跪姿提示词"
  }},
  "outfits": {{
    "casual": "日常装提示词",
    "formal": "正装提示词",
    "combat": "战斗装提示词"
  }}
}}
```"""

SCENE_DESIGN_PROMPT = """你是一个AI漫剧场景设计专家，精通场景空间深度和氛围营造。

场景信息：
名称: {name}
描述: {description}
氛围: {atmosphere}

【场景设计三维度】
1. 定位：场景类型（城市/自然/室内/科幻/古风等）
2. 时间/天气：时刻+光线/天气
3. 交互细节：飘落樱花/全息投影/地面倒影等

【提示词公式】
【风格】+【场景描述】+【时间天气】+【光影氛围】+【交互细节】+【质量词】| 负面提示词

【光影类型】
逆光、侧光、顶光、伦勃朗光、剪影、轮廓光、体积光、丁达尔效应

【色调类型】
暖色调、冷色调、高饱和、低饱和、黑白、赛博朋克、复古胶片

请生成JSON格式的场景设计卡：
```json
{{
  "scene_sheet": {{
    "name": "场景名称",
    "design_notes": "设计说明",
    "key_elements": ["关键元素1", "关键元素2"],
    "color_palette": "主色调",
    "atmosphere_guide": "氛围指南",
    "spatial_depth": "空间层次描述（前景/中景/背景）"
  }},
  "main_view": "主视角提示词（风格+场景描述+时间天气+光影氛围+交互细节+质量词+负面提示词）",
  "variants": {{
    "day": "白天版（光线充足、色调明亮）",
    "night": "夜晚版（月光/灯光、色调暗沉）",
    "sunset": "黄昏版（金色光线、暖色调）",
    "rain": "雨天版（湿润反光、冷色调）",
    "snow": "雪天版（白色覆盖、冷色调）"
  }},
  "detail_shots": {{
    "wide": "远景提示词（展现宏大场景、环境为主）",
    "medium": "中景提示词（展示空间关系）",
    "close": "近景提示词（聚焦细节元素）"
  }}
}}
```"""

NOVEL_ADAPTATION_PROMPT = """你是一个专业的小说改编剧本专家，擅长将长篇小说压缩改编为高密度短剧。

【改编原则】
1. 保留原著核心冲突和情感线
2. 将叙述性文字转化为可视化画面
3. 对话口语化，符合短剧节奏
4. 删除无关支线，聚焦主线
5. 增强戏剧冲突，加快节奏
6. 为每个场景设计AI绘图提示词
7. 保持人物性格一致性
8. 为每个角色生成完整的设计卡和三视图AI提示词
9. 为每个道具生成AI绘图提示词

请将以下小说内容改编为短剧剧本：

{novel_content}

请按以下JSON格式输出，每个字段都要尽量详细：
```json
{{
  "title": "剧名",
  "genre": "题材",
  "logline": "一句话概括",
  "synopsis": "剧情梗概（300-500字）",
  "theme": "核心主题",
  "emotional_tone": "情感基调",
  "characters": [
    {{
      "name": "角色名",
      "age": "年龄",
      "identity": "身份",
      "personality": "性格特点（3-5个关键词）",
      "appearance": "详细外貌描述（发型发色、瞳色、肤色、身材、标志性特征）",
      "clothing": "日常穿着描述",
      "signature_element": "标志性元素（口头禅/饰品/小动作）",
      "arc": "角色成长弧线",
      "relationships": {{}},
      "background_story": "角色背景故事",
      "three_view_prompt": "三视图AI绘图提示词（正面、侧面、背面，包含完整外貌服装描述）",
      "portrait_prompt": "特写肖像AI绘图提示词",
      "expression_prompts": {{
        "happy": "开心表情提示词",
        "angry": "愤怒表情提示词",
        "sad": "悲伤表情提示词",
        "determined": "坚定表情提示词"
      }}
    }}
  ],
  "scenes": [
    {{
      "name": "场景名",
      "description": "详细描述",
      "atmosphere": "氛围",
      "scene_prompt": "场景AI绘图提示词（包含风格、光影、氛围）",
      "scene_variants": {{
        "day": "白天版本提示词",
        "night": "夜晚版本提示词"
      }}
    }}
  ],
  "props": [
    {{
      "name": "道具名",
      "description": "描述和象征意义",
      "first_appearance": "首次出现集数",
      "prop_prompt": "道具AI绘图提示词"
    }}
  ],
  "world_rules": ["世界观规则1", "规则2"],
  "episodes": [
    {{
      "episode_number": 1,
      "title": "集标题",
      "summary": "概要",
      "hook": "开头钩子",
      "cliffhanger": "结尾悬念",
      "key_conflict": "核心冲突",
      "emotional_arc": "情感弧线",
      "shots": [
        {{
          "shot_number": 1,
          "shot_type": "景别（远景/全景/中景/近景/特写/大特写/主观视角）",
          "camera_movement": "运镜（固定/慢推/快推/缓拉/快拉/移镜/摇镜/跟镜/升降/环绕/手持）",
          "transition": "转场（硬切/渐变/叠化/黑场）",
          "frame_content": "画面内容（精确到人物姿态、表情、环境细节）",
          "dialogue": "台词（含情绪标注）",
          "sound_effects": "音效",
          "duration": 3.0,
          "ai_prompt": "AI绘图提示词（风格+主体+场景+动作+镜头+光影+约束词）",
          "lighting": "光影",
          "emotion": "情绪",
          "hook_type": "钩子类型",
          "hook_detail": "钩子分析"
        }}
      ]
    }}
  ]
}}
```"""


class ScriptGenerator:
    """Multi-phase script generator with knowledge base management."""

    def __init__(self):
        self._active_tasks: dict[str, ScriptResponse] = {}

    async def start_generation(self, request: ScriptRequest) -> str:
        """Start async script generation. Returns task ID."""
        task_id = str(uuid.uuid4())[:8]
        project_id = f"project_{task_id}"

        self._active_tasks[task_id] = ScriptResponse(
            id=task_id,
            status="generating",
            progress=0.0,
            total_episodes=request.episode_count,
        )

        asyncio.create_task(self._generate_script(task_id, project_id, request))
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[ScriptResponse]:
        return self._active_tasks.get(task_id)

    async def _generate_script(self, task_id: str, project_id: str, request: ScriptRequest):
        """Full script generation pipeline."""
        kb = KnowledgeBase(project_id)

        try:
            # Phase 1: Story Planning
            self._active_tasks[task_id].progress = 5.0
            story_plan = await self._plan_story(request)
            if not story_plan:
                raise Exception("故事策划失败，请检查AI配置")

            # Initialize knowledge base
            self._init_knowledge_base(kb, story_plan)
            self._active_tasks[task_id].progress = 15.0

            # Phase 2: Generate character designs
            characters = []
            for char_data in story_plan.get("characters", []):
                # Ensure all fields are strings (AI may return int for age)
                def s(v):
                    return str(v) if v is not None else ""

                char = Character(
                    name=s(char_data.get("name", "")),
                    age=s(char_data.get("age", "")),
                    identity=s(char_data.get("identity", "")),
                    personality=s(char_data.get("personality", "")),
                    appearance=s(char_data.get("appearance", "")),
                    clothing=s(char_data.get("clothing", "")),
                    signature_element=s(char_data.get("signature_element", "")),
                    arc=s(char_data.get("arc", "")),
                    relationships=char_data.get("relationships", {}) if isinstance(char_data.get("relationships"), dict) else {},
                    # Support both old and new field names
                    ai_prompt=s(char_data.get("three_view_prompt", char_data.get("ai_prompt", char_data.get("ai_prompt_cn", "")))),
                )
                characters.append(char)

            self._active_tasks[task_id].progress = 20.0

            # Phase 3: Generate each episode
            episodes = []
            for ep_num in range(1, request.episode_count + 1):
                self._active_tasks[task_id].current_episode = ep_num
                self._active_tasks[task_id].progress = 20.0 + (ep_num / request.episode_count) * 75.0

                ep_plan = {}
                ep_plans = story_plan.get("episode_plan", [])
                if ep_num <= len(ep_plans):
                    ep_plan = ep_plans[ep_num - 1]

                context = kb.get_context_for_episode(ep_num)
                try:
                    episode = await self._generate_episode(ep_num, request, story_plan, ep_plan, context)
                except Exception as ep_err:
                    logger.error(f"Episode {ep_num} generation failed: {ep_err}")
                    episode = Episode(
                        episode_number=ep_num,
                        title=f"第{ep_num}集",
                        summary=f"生成失败: {str(ep_err)[:100]}",
                    )

                if episode:
                    episodes.append(episode)
                    kb.save_episode(episode)
                    kb.extract_entities_from_episode(episode)

            # Phase 4: Build final script
            script = Script(
                id=task_id,
                title=story_plan.get("title", request.topic),
                genre=request.genre,
                logline=story_plan.get("logline", ""),
                synopsis=story_plan.get("synopsis", ""),
                characters=characters,
                episodes=episodes,
                theme=story_plan.get("theme", ""),
                emotional_tone=story_plan.get("emotional_tone", ""),
                target_audience=request.target_audience,
                style=request.style,
            )

            # Store scene and prop data in the script's synopsis (extended)
            script_data = script.model_dump()
            script_data["scenes"] = story_plan.get("scenes", [])
            script_data["props"] = story_plan.get("props", [])

            self._active_tasks[task_id].script = script
            self._active_tasks[task_id].status = "completed"
            self._active_tasks[task_id].progress = 100.0

            # Store extended data
            self._active_tasks[task_id]._extended_data = script_data

        except Exception as e:
            logger.error(f"Script generation failed: {e}", exc_info=True)
            self._active_tasks[task_id].status = "failed"
            self._active_tasks[task_id].error = str(e)

    async def _plan_story(self, request: ScriptRequest) -> dict:
        """Phase 1: Generate overall story plan."""
        trend_context = ""
        if request.trend_context:
            trend_context = f"""

【热点灵感参考】（重要：仅提取核心创意元素和情感共鸣点，绝对不要直接复制标题或描述，必须原创一个全新的故事）
{request.trend_context}

请从以上热点中提取：
- 吸引观众的核心情感点（如逆袭、复仇、甜宠等）
- 受欢迎的题材设定元素
- 目标受众的偏好特征
然后基于这些元素，创作一个全新的、有原创性的故事。"""

        prompt = f"""请为以下短剧主题生成完整的策划方案：

主题: {request.topic}
题材: {request.genre.value}
集数: {request.episode_count}集
每集时长: {request.episode_duration}秒
目标受众: {request.target_audience}
风格: {request.style}
特殊要求: {request.special_requirements}
{trend_context}

请严格按照系统提示中的JSON格式输出完整方案。特别注意：
1. 故事必须原创，不要直接套用热点标题或简介
2. 每个角色都要有完整的三视图AI绘图提示词
3. 每个场景都要有AI绘图提示词和多个变体
4. 重要道具也要有AI绘图提示词
5. 表情和动作的提示词要详细可用
6. 【最重要】必须设计一个贯穿全剧的核心悬念钩子（core_mystery），在第1集开头就展示出来，但答案要到至少第5集之后才逐步揭晓。这个悬念是观众持续观看的核心动力。
7. AI绘图提示词参考Seedance 2.0标准：风格先行、主体描述精准、动作写慢不写快、镜头语言明确"""

        messages = [
            {"role": "system", "content": STORY_PLANNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await ai_client.chat(messages, temperature=0.9, max_tokens=8192)
        result = self._extract_json(response)
        if not result:
            logger.error(f"Story planning returned empty JSON. Response was: {response[:500]}")
        return result

    async def _generate_episode(self, ep_num: int, request: ScriptRequest, story_plan: dict, ep_plan: dict, context: str) -> Episode:
        """Phase 2: Generate a single episode with full storyboard."""
        characters_info = ""
        for c in story_plan.get("characters", []):
            characters_info += f"- {c.get('name')}: {c.get('identity')}, {c.get('personality')}, {c.get('appearance')}\n"

        prev_episode_summary = ""
        if ep_num > 1:
            prev_episode_summary = f"\n上一集概要：\n{context}"

        ep_plan_text = ""
        if ep_plan:
            ep_plan_text = f"""
本集计划：
- 标题: {ep_plan.get('title', '')}
- 核心冲突: {ep_plan.get('key_conflict', '')}
- 关键事件: {', '.join(ep_plan.get('key_events', []))}
- 开头钩子: {ep_plan.get('hook', '')}
- 结尾悬念: {ep_plan.get('cliffhanger', '')}
- 情感弧线: {ep_plan.get('emotional_arc', '')}
"""

        core_mystery = story_plan.get("core_mystery", {})
        mystery_context = ""
        if ep_num == 1 and core_mystery:
            mystery_context = f"""

【核心悬念钩子】（最重要！）
本剧核心悬念: {core_mystery.get('description', '')}
揭晓集数: 第{core_mystery.get('reveal_episode', '?')}集之后
第1集开头必须展示的震撼场景: {core_mystery.get('hook_scene', '')}
这个悬念要在开头3秒内以最震撼的方式呈现，让观众产生强烈好奇心！"""

        prompt = f"""请为第{ep_num}集生成完整的分镜脚本。

剧名: {story_plan.get('title', '')}
题材: {request.genre.value}
总集数: {request.episode_count}
每集时长: {request.episode_duration}秒
风格: {request.style}

角色信息:
{characters_info}
{ep_plan_text}
{prev_episode_summary}

知识库上下文:
{context}
{mystery_context}

请严格按照系统提示中的JSON格式输出。确保：
1. 开头3秒是强钩子{'' if ep_num > 1 else '（第1集必须是核心悬念钩子，要足够震撼）'}
2. 每个分镜都有完整的AI绘图提示词（Seedance 2.0标准：风格先行、描述精准、动作写慢不写快）
3. 台词口语化、有网感
4. 结尾是悬念
5. 与前几集保持剧情连贯
6. ai_prompt使用Seedance 2.0标准格式：风格+主体+场景+动作+镜头+光影+约束词"""

        messages = [
            {"role": "system", "content": EPISODE_GENERATOR_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await ai_client.chat(messages, temperature=0.85, max_tokens=8192)
        data = self._extract_json(response)

        if not data:
            return Episode(
                episode_number=ep_num,
                title=f"第{ep_num}集",
                summary="生成失败",
            )

        shots = []
        for s in data.get("shots", []):
            shots.append(Shot(
                shot_number=s.get("shot_number", 0),
                shot_type=s.get("shot_type") or "",
                camera_movement=s.get("camera_movement") or "",
                frame_content=s.get("frame_content") or "",
                dialogue=s.get("dialogue") or "",
                sound_effects=s.get("sound_effects") or "",
                duration=s.get("duration") or 3.0,
                # Support both old and new field names
                ai_prompt=s.get("ai_prompt") or s.get("ai_prompt_cn") or "",
                lighting=s.get("lighting") or "",
                emotion=s.get("emotion") or "",
                notes=s.get("notes") or "",
                hook_type=s.get("hook_type"),
                hook_detail=s.get("hook_detail") or "",
            ))

        return Episode(
            episode_number=ep_num,
            title=data.get("title", f"第{ep_num}集"),
            summary=data.get("summary", ""),
            hook=data.get("hook", ""),
            cliffhanger=data.get("cliffhanger", ""),
            shots=shots,
            total_duration=data.get("total_duration", request.episode_duration),
            key_conflict=data.get("key_conflict", ""),
            emotional_arc=data.get("emotional_arc", ""),
        )

    def _init_knowledge_base(self, kb: KnowledgeBase, story_plan: dict):
        """Initialize knowledge base from story plan."""
        for c in story_plan.get("characters", []):
            entity = KnowledgeEntity(
                name=c.get("name", ""),
                entity_type="character",
                description=f"{c.get('identity', '')} - {c.get('personality', '')}",
                attributes={
                    "age": c.get("age", ""),
                    "appearance": c.get("appearance", ""),
                    "clothing": c.get("clothing", ""),
                    "signature_element": c.get("signature_element", ""),
                    "arc": c.get("arc", ""),
                    "relationships": c.get("relationships", {}),
                    "background_story": c.get("background_story", ""),
                },
            )
            kb.add_entity(entity)

        # Add scenes
        for scene in story_plan.get("scenes", []):
            entity = KnowledgeEntity(
                name=scene.get("name", ""),
                entity_type="location",
                description=scene.get("description", ""),
                attributes={
                    "atmosphere": scene.get("atmosphere", ""),
                    "time_of_day": scene.get("time_of_day", ""),
                },
            )
            kb.add_entity(entity)

        # Add props
        for prop in story_plan.get("props", []):
            entity = KnowledgeEntity(
                name=prop.get("name", ""),
                entity_type="item",
                description=prop.get("description", ""),
                attributes={
                    "first_appearance": prop.get("first_appearance", ""),
                },
            )
            kb.add_entity(entity)

        for rule in story_plan.get("world_rules", []):
            kb.add_world_rule(rule)

        for thread in story_plan.get("plot_threads", []):
            kb.add_plot_thread(
                name=thread.get("name", ""),
                description=thread.get("description", ""),
            )

        for fs in story_plan.get("foreshadowing", []):
            kb.add_foreshadowing(
                setup=fs.get("setup", ""),
                episode=fs.get("episode", 1),
                payoff_episode=fs.get("payoff_episode", 0),
            )

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from AI response text with robust parsing."""
        if not text or not text.strip():
            return {}

        # Strategy 1: Extract from markdown code block (greedy match for nested braces)
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', text)
        if json_match:
            result = self._try_parse_json(json_match.group(1))
            if result:
                return result

        # Strategy 2: Find the outermost { } pair by counting braces
        start = text.find('{')
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        result = self._try_parse_json(text[start:i + 1])
                        if result:
                            return result
                        break

        # Strategy 3: Regex fallback (greedy)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = self._try_parse_json(json_match.group(0))
            if result:
                return result

        logger.warning(f"Failed to extract JSON from response (length={len(text)}): {text[:200]}...")
        return {}

    def _try_parse_json(self, text: str) -> dict:
        """Try to parse JSON with common fixups."""
        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fix common issues from LLM output
        fixed = text
        # Remove single-line comments (must be before newline fix)
        fixed = re.sub(r'//.*?\n', '\n', fixed)
        # Remove trailing commas before } or ]
        fixed = re.sub(r',\s*([\]}])', r'\1', fixed)
        # Fix unescaped newlines in strings
        fixed = fixed.replace('\n', '\\n') if '\\n' not in fixed else fixed

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Last resort: try to fix truncated JSON by closing open brackets
        try:
            depth_curly = 0
            depth_square = 0
            in_string = False
            escape = False
            for ch in fixed:
                if escape:
                    escape = False
                    continue
                if ch == '\\' and in_string:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth_curly += 1
                elif ch == '}':
                    depth_curly -= 1
                elif ch == '[':
                    depth_square += 1
                elif ch == ']':
                    depth_square -= 1

            if depth_curly > 0 or depth_square > 0:
                # Close any open strings first
                if in_string:
                    fixed += '"'
                fixed += ']' * depth_square + '}' * depth_curly
                return json.loads(fixed)
        except (json.JSONDecodeError, Exception):
            pass

        return {}

    async def adapt_novel(self, novel_content: str, episode_count: int = 8, genre: ScriptGenre = ScriptGenre.REBIRTH, style: str = "古风") -> dict:
        """Convert a novel into a drama script with multi-phase processing.

        Multi-phase pipeline:
        1. Split novel into chapters, extract overview
        2. Generate story plan (characters, scenes, props, world rules) via LLM
        3. Generate detailed character/scene/prop design cards via LLM
        4. Generate per-episode full storyboards via LLM with knowledge base context
        5. Assemble final result
        """
        # Phase 1: Split novel into chapters and extract overview
        chapters = self._split_chapters(novel_content)
        logger.info(f"Novel split into {len(chapters)} chapters")

        overview_text = "\n\n".join(chapters[:5])[:8000]
        overview = await self._extract_novel_overview(overview_text, genre.value, style)
        logger.info(f"Novel overview extracted: {overview.get('title', 'unknown')}")

        # Build condensed novel for AI
        chapter_summaries = []
        if len(chapters) > 10:
            sample_indices = list(range(min(5, len(chapters))))
            mid = len(chapters) // 2
            sample_indices.extend([mid - 1, mid, mid + 1])
            sample_indices.extend(range(max(0, len(chapters) - 3), len(chapters)))
            sample_indices = sorted(set(i for i in sample_indices if 0 <= i < len(chapters)))
            for idx in sample_indices:
                summary = chapters[idx][:1000]
                chapter_summaries.append(f"第{idx+1}章摘要: {summary}")

        if len(chapters) <= episode_count * 2:
            condensed = novel_content[:20000]
        else:
            chapters_per_ep = len(chapters) / episode_count
            selected = []
            for ep in range(episode_count):
                start_idx = int(ep * chapters_per_ep)
                end_idx = int((ep + 1) * chapters_per_ep)
                if start_idx < len(chapters):
                    selected.append(chapters[start_idx][:1500])
                if end_idx - 1 > start_idx and end_idx - 1 < len(chapters):
                    selected.append(chapters[end_idx - 1][:1500])
            condensed = "\n\n[分隔]\n\n".join(selected)[:20000]

        novel_context = f"""【小说基本信息】
标题: {overview.get('title', '未知')}
题材: {genre.value}
风格: {style}
主要角色: {', '.join(overview.get('main_characters', []))}
核心冲突: {overview.get('core_conflict', '')}
故事梗概: {overview.get('synopsis', '')}

【原著关键章节】
{condensed}
"""
        if chapter_summaries:
            novel_context += f"\n\n【章节摘要】\n{chr(10).join(chapter_summaries[:15])}"

        # Phase 2: Generate story plan (characters, scenes, props, world rules)
        logger.info("Phase 2: Generating story plan from novel...")
        story_plan = await self._adapt_story_plan(novel_context, genre.value, style, episode_count)
        if not story_plan:
            logger.error("Story plan generation failed, falling back to single-shot adaptation")
            return await self._adapt_novel_single_shot(novel_context)

        # Phase 3: Enhance character/scene/prop designs with detailed AI prompts
        logger.info("Phase 3: Generating detailed asset designs...")
        enhanced_plan = await self._enhance_asset_designs(story_plan)

        # Phase 4: Generate per-episode storyboards using knowledge base
        logger.info("Phase 4: Generating per-episode storyboards...")
        kb = KnowledgeBase(f"novel_adapt_{uuid.uuid4().hex[:8]}")
        self._init_knowledge_base(kb, enhanced_plan)

        episodes = []
        for ep_num in range(1, episode_count + 1):
            logger.info(f"Generating episode {ep_num}/{episode_count}...")
            ep_plan = {}
            ep_plans = enhanced_plan.get("episode_plan", [])
            if ep_num <= len(ep_plans):
                ep_plan = ep_plans[ep_num - 1]

            context = kb.get_context_for_episode(ep_num)
            try:
                episode = await self._generate_episode(
                    ep_num,
                    ScriptRequest(
                        topic=enhanced_plan.get("title", "改编剧本"),
                        genre=genre,
                        episode_count=episode_count,
                        style=style,
                    ),
                    enhanced_plan,
                    ep_plan,
                    context,
                )
                episodes.append(episode.model_dump())
                kb.save_episode(episode)
                kb.extract_entities_from_episode(episode)
            except Exception as e:
                logger.error(f"Episode {ep_num} generation failed: {e}")
                episodes.append({
                    "episode_number": ep_num,
                    "title": f"第{ep_num}集",
                    "summary": f"生成失败: {str(e)[:100]}",
                    "shots": [],
                })

        # Phase 5: Assemble final result
        result = {
            "title": enhanced_plan.get("title", overview.get("title", "未命名剧本")),
            "genre": genre.value,
            "logline": enhanced_plan.get("logline", ""),
            "synopsis": enhanced_plan.get("synopsis", overview.get("synopsis", "")),
            "theme": enhanced_plan.get("theme", ""),
            "emotional_tone": enhanced_plan.get("emotional_tone", ""),
            "characters": enhanced_plan.get("characters", []),
            "scenes": enhanced_plan.get("scenes", []),
            "props": enhanced_plan.get("props", []),
            "world_rules": enhanced_plan.get("world_rules", []),
            "episodes": episodes,
        }
        logger.info(f"Novel adaptation complete: {result['title']} with {len(episodes)} episodes")
        return result

    async def _adapt_story_plan(self, novel_context: str, genre: str, style: str, episode_count: int) -> dict:
        """Generate story plan from novel content."""
        prompt = f"""请基于以下小说内容，生成完整的短剧改编策划方案。

{novel_context}

要求：
- 改编为{episode_count}集短剧
- 保留原著核心冲突和情感线，但要重新结构化为短剧节奏
- 为每个角色生成完整设定（包含三视图AI绘图提示词）
- 为每个场景生成AI绘图提示词和变体
- 为重要道具生成AI绘图提示词
- 生成每集的计划大纲

请严格按照系统提示中的JSON格式输出。"""

        messages = [
            {"role": "system", "content": STORY_PLANNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await ai_client.chat(messages, temperature=0.8, max_tokens=8192)
        result = self._extract_json(response)
        return result

    async def _enhance_asset_designs(self, story_plan: dict) -> dict:
        """Enhance character, scene, and prop designs with detailed AI prompts."""
        enhanced = dict(story_plan)

        # Enhance characters
        enhanced_characters = []
        for char_data in story_plan.get("characters", []):
            name = char_data.get("name", "")
            if not name:
                enhanced_characters.append(char_data)
                continue

            # Check if character already has detailed prompts
            if char_data.get("three_view_prompt") and char_data.get("expression_prompts"):
                enhanced_characters.append(char_data)
                continue

            logger.info(f"Enhancing character design: {name}")
            try:
                enhanced_char = await self._generate_character_design(char_data)
                enhanced_characters.append(enhanced_char)
            except Exception as e:
                logger.error(f"Character design enhancement failed for {name}: {e}")
                enhanced_characters.append(char_data)

        enhanced["characters"] = enhanced_characters

        # Enhance scenes
        enhanced_scenes = []
        for scene_data in story_plan.get("scenes", []):
            name = scene_data.get("name", "")
            if not name:
                enhanced_scenes.append(scene_data)
                continue

            if scene_data.get("scene_prompt") and scene_data.get("scene_variants"):
                enhanced_scenes.append(scene_data)
                continue

            logger.info(f"Enhancing scene design: {name}")
            try:
                enhanced_scene = await self._generate_scene_design(scene_data)
                enhanced_scenes.append(enhanced_scene)
            except Exception as e:
                logger.error(f"Scene design enhancement failed for {name}: {e}")
                enhanced_scenes.append(scene_data)

        enhanced["scenes"] = enhanced_scenes

        return enhanced

    async def _generate_character_design(self, char_data: dict) -> dict:
        """Generate detailed character design with AI prompts."""
        prompt = CHARACTER_DESIGN_PROMPT.format(
            name=char_data.get("name", ""),
            identity=char_data.get("identity", ""),
            personality=char_data.get("personality", ""),
            appearance=char_data.get("appearance", ""),
            clothing=char_data.get("clothing", ""),
        )

        response = await ai_client.chat([
            {"role": "system", "content": "你是一个AI漫剧角色设计专家。请根据角色信息生成完整的设计卡。"},
            {"role": "user", "content": prompt},
        ], temperature=0.7, max_tokens=4096)

        design = self._extract_json(response)
        if not design:
            return char_data

        # Merge design into character data
        result = dict(char_data)
        if "three_view" in design:
            tv = design["three_view"]
            result["three_view_prompt"] = tv.get("front_view", "")
            result["three_view_side"] = tv.get("side_view", "")
            result["three_view_back"] = tv.get("back_view", "")
        if "portrait" in design:
            result["portrait_prompt"] = design["portrait"]
        if "expressions" in design:
            result["expression_prompts"] = design["expressions"]
        if "actions" in design:
            result["action_prompts"] = design["actions"]
        if "outfits" in design:
            result["outfit_prompts"] = design["outfits"]
        if "character_sheet" in design:
            result["design_philosophy"] = design["character_sheet"].get("design_philosophy", "")
            result["color_palette"] = design["character_sheet"].get("color_palette", "")
            dna = design["character_sheet"].get("dna_profile", {})
            if dna:
                result["dna_profile"] = dna

        return result

    async def _generate_scene_design(self, scene_data: dict) -> dict:
        """Generate detailed scene design with AI prompts."""
        prompt = SCENE_DESIGN_PROMPT.format(
            name=scene_data.get("name", ""),
            description=scene_data.get("description", ""),
            atmosphere=scene_data.get("atmosphere", ""),
        )

        response = await ai_client.chat([
            {"role": "system", "content": "你是一个AI漫剧场景设计专家。请根据场景信息生成完整的设计卡。"},
            {"role": "user", "content": prompt},
        ], temperature=0.7, max_tokens=4096)

        design = self._extract_json(response)
        if not design:
            return scene_data

        result = dict(scene_data)
        if "main_view" in design:
            result["scene_prompt"] = design["main_view"]
        if "variants" in design:
            result["scene_variants"] = design["variants"]
        if "detail_shots" in design:
            result["detail_shots"] = design["detail_shots"]
        if "scene_sheet" in design:
            result["design_notes"] = design["scene_sheet"].get("design_notes", "")
            result["key_elements"] = design["scene_sheet"].get("key_elements", [])
            result["spatial_depth"] = design["scene_sheet"].get("spatial_depth", "")

        return result

    async def _adapt_novel_single_shot(self, novel_context: str) -> dict:
        """Fallback: single-shot novel adaptation when multi-phase fails."""
        prompt = NOVEL_ADAPTATION_PROMPT.format(novel_content=novel_context)
        messages = [
            {"role": "system", "content": "你是一个专业的小说改编剧本专家，精通AI漫剧创作。请基于提供的小说内容，生成完整的短剧剧本。"},
            {"role": "user", "content": prompt},
        ]

        response = await ai_client.chat(messages, temperature=0.8, max_tokens=8192)
        result = self._extract_json(response)
        return result

    def _split_chapters(self, text: str) -> list[str]:
        """Split novel text into chapters using common patterns."""
        # Common chapter patterns
        patterns = [
            r'\n\s*第[一二三四五六七八九十百千\d]+[章回节卷集部]\s*',
            r'\n\s*Chapter\s*\d+',
            r'\n\s*\d+\.\s+',
            r'\n\s*【第[一二三四五六七八九十百千\d]+[章回节]】',
            r'\n\s*[=]{3,}\s*\n',
            r'\n\s*[-]{3,}\s*\n',
        ]

        # Try each pattern
        for pattern in patterns:
            splits = re.split(f'({pattern})', text)
            if len(splits) > 3:  # Found meaningful splits
                chapters = []
                current = ""
                for part in splits:
                    if re.match(pattern, part):
                        if current.strip():
                            chapters.append(current.strip())
                        current = part
                    else:
                        current += part
                if current.strip():
                    chapters.append(current.strip())
                # Filter out very short chapters
                chapters = [c for c in chapters if len(c) > 100]
                if len(chapters) >= 3:
                    return chapters

        # Fallback: split by double newlines into chunks
        chunks = re.split(r'\n\s*\n\s*\n', text)
        chunks = [c.strip() for c in chunks if len(c.strip()) > 100]
        if len(chunks) >= 3:
            return chunks

        # Final fallback: equal-length chunks
        chunk_size = max(2000, len(text) // 20)
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    async def _extract_novel_overview(self, text: str, genre: str, style: str) -> dict:
        """Extract novel overview from early chapters."""
        prompt = f"""请从以下小说开头内容中提取关键信息，输出JSON格式：

{text[:6000]}

```json
{{
  "title": "小说标题",
  "main_characters": ["主要角色1", "主要角色2", "主要角色3"],
  "core_conflict": "核心冲突（50字内）",
  "synopsis": "故事梗概（200字内）",
  "setting": "故事背景",
  "time_period": "时代背景",
  "key_relationships": "关键人物关系"
}}
```"""

        try:
            response = await ai_client.chat([
                {"role": "system", "content": "你是一个小说分析专家，擅长提取小说核心信息。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3, max_tokens=1000)
            return self._extract_json(response)
        except Exception as e:
            logger.error(f"Novel overview extraction failed: {e}")
            return {"title": "未命名", "main_characters": [], "core_conflict": "", "synopsis": ""}


script_generator = ScriptGenerator()
