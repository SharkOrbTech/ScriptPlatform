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

STORY_PLANNER_PROMPT = """你是一个顶级短剧编剧策划专家，精通爆款短剧创作方法论。

【核心原则】短剧 = 情绪 > 情节。所有情节、台词、人物都服务于一个目标：在最短的时间内，用最强的方式拉扯观众的情绪。
三条铁律：不要废话（快进矛盾但保留必要过渡）、不要想当然（写市场需要的）、用不到天赋（靠套路公式）。

【整体结构框架】
- 单集内部结构：10%-80%-10%黄金比例
  - 起因（10%）：以强烈冲突动作开场（扇耳光、掀桌子、绑架、车祸），零铺垫
  - 经过（80%）：反派持续施压，主角隐忍/被误解，观众情绪被反复拉扯
  - 结果/钩子（10%）：留悬念设卡点，让观众想看下一集。悬念可以是信息差、人物决定、情感转折
- 每集2-3个场景，台词占大头，第1集信息密度最高

【剧集整体节奏】
- 第1-2集：开篇炸裂，建立核心冲突（情绪最高点→悬疑钩子）
- 第3-10集：交代人物关系、主线目标，持续压主角（压抑→小爽→再压抑）
- 第11-20集：主线推进，配角出场制造障碍（持续拉扯）
- 第20-40集：中段高潮，误会加深，身份悬疑（情绪递进）
- 第40-60集：转折期，真相逐步浮现（希望→失望交替）
- 第60-80集：终极冲突，反派最后反扑（紧张感最高）
- 第80-100集：大结局，所有线索收束（爽感爆发→圆满）
- 第100-150集（超长剧）：多条支线展开，新势力登场，中期大反转，分阶段收束
- 第150-200集（超长剧）：主线分幕推进，每50集一个小高潮，最终大决战
- 付费卡点：第8-10集设第一个付费卡点，后续每20集左右设一个

【钩子技法体系】
开头钩子类型（必须在3秒内抓住观众）：
A. 暴力冲突开场：直接展示极端冲突（砸酒瓶、扇耳光、绑架）
B. 身份反转开场：开场即展示核心矛盾（前世结局→重生→改变命运）
C. 极端情绪开场：制造强烈情绪冲击（大哭、紧张、大骂、惨叫）
D. 悬念/恐怖开场：营造阴森氛围、紧张感拉满

集末钩子七大类型：
A. 关键时刻被打断：谈话聊到关键部分突然停止
B. 人物表情反转：突然露出不可思议/害怕/疑惑表情后卡点
C. 危机即将爆发：女佣正要拿棒球棍打女主——卡点
D. 身份即将揭露：每次接近揭露时卡点，下一集反转
E. 新人物/势力出场：被打脸的反派找到更强大靠山
F. 情绪高潮卡点：打斗高潮处、暧昧最撩人瞬间
G. 信息差制造悬念：电话打来，表情凝重，台词"不好了""坏了"

钩子密度：1-10集每集1个钩子；10-30集每1-2集1个；30集以后最多2集无钩子

【伏笔技法】
A. 信物伏笔：道具贯穿全剧，每次接近暴露又收回
B. 身份伏笔：各路大佬对主角的态度暗示真实身份
C. 闪回伏笔：前世记忆作为伏笔，让主角"预知"阴谋
D. 对话伏笔：通过配角对话透露关键信息
E. 道具伏笔：手镯、信件、照片等物品反复出现

【反转技法】
A. 身份反转（最核心爽点）：被嘲讽→揭示真实身份→嘲讽者跪地求饶
B. 关系反转：仇人实为恩人，盟友实为敌人
C. 局势反转：绝境中的反击，将计就计
D. 认知反转：观众有上帝视角但剧中人不知

【角色塑造原则】
- 扁平化与极致化：个性鲜明一边倒，反派言语粗俗行为粗鄙
- 人物标签化：霸总就要有霸总的样子
- 反差人设模板：
  1. 表面冷酷无情→实则宠妻狂魔（男主人设No.1）
  2. 表面憨厚老实→实则扮猪吃老虎（逆袭类必备）
  3. 表面柔弱可怜→实则白切黑（女主人设No.1）
  4. 表面花心浪荡→实则深情专一
- 角色出场：主角先展示困境引发同情；反派直接展示恶行建立仇恨值
- 反派升级机制：套娃式出场，每个被打脸的反派背后有更大势力
- 反派要有具体的恶行细节（踩脸、扇巴掌、撕衣服、泼水），不能抽象概括
- 每个反派都要有具体的恶行细节（踩脸、扇巴掌、撕衣服、泼水），不能抽象概括

【冲突升级模式】（每集1-2层，逐层递进）
压迫→小反击→更大压迫→最终反杀（螺旋上升）：
- 第一层：言语侮辱（"废物""贱种""你也配？"）
- 第二层：肢体暴力/权力碾压（扇耳光、推搡、踩脸）
- 第三层：关系破坏（离间、诬陷栽赃）
- 第四层：经济/生存威胁（剥夺财产、断绝生路）
- 第五层：生命威胁（绑架、下毒、直接下死手）
要求：冲突逐层递进，不必一集用满五层，1-2层即可。愤怒通过多集累积发酵。

【"压-爽"节奏】（至少1个循环，允许跨集）
- 至少1个"压-爽"循环，可跨2-3集完成完整的压抑→释放弧线
- 持续压抑后的爆发更有冲击力，不必每集都爽
- 压抑时间占60-70%，释放瞬间占30-40%
- 情绪递进比"每个单元都完整"更重要

【剧情推进节奏】（自然推进，不要赶）
- 对白是推进事件的主要手段，不要用旁白喧宾夺主
- 允许角色反应、停顿、酝酿情绪的过渡镜头
- 情感递进比信息密度更重要：先让观众感受到，再让观众知道
- 同一个情绪点可在不同集数中重复强化

【旁白】（仅限内心独白）
旁白仅用于角色内心独白（OS），展示角色内心真实想法，配合表情特写。
- 例："我不能再犹豫了，这一次的决定将改变一切"
- 例："我发誓，这辈子不会再让任何人欺负我"
- 使用规则：
  - 旁白字数灵活，不设硬性目标，如果生硬就省略
  - 同一镜头中旁白和台词互斥，只能出现一个
  - 禁止解说旁白和回忆旁白，所有信息优先通过对白传递
  - 台词是叙事的核心驱动力

【信息释放策略】
- 三层信息差：观众知道而角色不知道（上帝视角）、角色知道而观众不知道（悬念）、反派知道而主角不知道（危机感）
- 背景信息优先通过对白带出，避免大段叙述
- 身份揭露节奏：不能一次揭露完，每次快揭露时反转，延迟到付费卡点之后

【30个爽感来源（剧情中自然融入）】
身份碾压、能力碾压、财富碾压、人脉碾压、情感碾压、绝境反杀、扮猪吃老虎、重生改变命运、大佬对小人物恭敬、聚会遭歧视后大人物对主角点头哈腰等

【对白要求】（台词是短剧的灵魂）
- 每集台词量 = 时长秒数 × (5~8)字，第1集最密，后续集可适当灵活
- 台词简短有力，每句只抛一个信息
- 口语化接地气，不秀文笔
- 反派得意时可主动揭露阴谋（"你还不知道吧？你爸妈是我撞死的！"），这是爽感来源
- 高频台词模式：侮辱施压型、反转型、身份揭露型、情感拉扯型
- 旁白仅限内心独白，字数灵活，如不自然可省略

【反派七类阴险套路】（参考）
一、强拆CP：抢主角女神、利用性格缺陷制造矛盾、炫耀成就让主角自卑
二、扮猪吃老虎：装可怜引起同情、装正义搜集黑历史、伪装跟班伺机出手
三、冤枉陷害：暗中算计、散播谣言、陷害入狱、假扮盟友
四、利用算计：利用仁慈之心、利用对亲人的感情、利用弱点
五、麻烦制造机：利用恋爱/亲人/缺点/仇恨制造麻烦
六、麻烦危机：制造障碍、偷盗财物、假扮朋友、利用家族/软肋
七、反复背叛：在最困难时扮演救世主再背叛、相处成朋友后密谋背叛

【危机感塑造三法】
1. 信息差：主角身边的人不知道主角早就帮自己解决了麻烦，自己去找反派却被威胁
2. 时间锁：给任务设定时间限制，利用时间压力构造紧迫感（最后一秒钟营救）
3. 生死局：主角陷入危机，一旦无法解决就会死，最常见的是赌局

【八种剧情写法】（根据题材灵活选用）
1. 侮辱和背叛：被男友、闺蜜、亲近的人侮辱、背叛
2. 误会：被男主无脑误会
3. 暴力对待：身体暴力、情感暴力
4. 肢体冲突、情感冲突：虐身虐心
5. 言语攻击：配角对主角的言语攻击
6. 不信守承诺：人物出尔反尔
7. 童年阴影：某种行为是童年遭受阴影导致的
8. 欺诈：观众有上帝视角，知道人物被欺诈，而剧中人物不知道

【六大矛盾来源】
1. 男主和女主的矛盾
2. 男主和女配的矛盾
3. 女主和女配的矛盾
4. 女主和男配的矛盾
5. 男主和男配的矛盾
6. 角色与自身价值观的冲突

【20个出圈反差人设】（参考选择一个应用）
1. 花心到处撩人→血性男儿一往无前
2. 温文尔雅→内心阴暗心机深沉
3. 飞檐走壁武功高强→憨厚耿直呆头呆脑
4. 咸鱼躺平佛系→能力出众办事效率极高
5. 身娇体弱病弱少年→精明阴险手段毒辣
6. 不近女色清心寡欲→恋爱脑痴情一片
7. 心狠手辣暴怒狂虐→撒娇黏人铁憨憨
8. 心直口快爱怼人→认怂求放过胆小鬼
9. 杀伐果断冷酷无情→硬汉娇夫小奶狗
10. 运筹帷幄执掌大权→内心脆弱可怜无助
11. 憨厚耿直好欺负→无比精明扮猪吃老虎
12. 离经叛道野蛮生长→人间清醒专治不服
13. 睚眦必报武力爆表→内心柔弱小哭包
14. 不学无术纨绔子弟→深情专一博学多才
15. 柔弱不能自理小哭包→白切黑疯批毁天灭地
16. 高岭之花冷清大女主→恋爱脑粘人小妖精
17. 茶言茶语又坏又作→人间清醒聪明机敏
18. 八面玲珑交际厉害→孤独缺爱内心柔软
19. 娇蛮任性横冲直撞→心软善良内心单纯
20. 聪明善解人意邻家→心机深沉狠辣江湖女

【核心禁忌】
禁止：铺垫太多切入太慢、背景太过冗长、描写不具体、台词秀文笔、一个人物长篇幅自说自话、对话含蓄委婉
禁止用力过猛：不要每集都掀桌/耳光/下跪/车祸，戏剧张力来自人物关系和处境而非极端动作

【输出要求】
请严格按以下JSON格式输出，不要包含任何其他文字。
【重要】请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记。

{
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
      "hook": "开头钩子（第1集用核心悬念开场，后续集可灵活处理）",
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
}"""

EPISODE_GENERATOR_PROMPT = """你是一个顶级短剧分镜脚本专家，精通AI绘图提示词工程和爆款短剧创作方法论。

【单集结构公式：10%-80%-10%黄金比例】
- 起因（10%）：以明确的戏剧张力开场（紧张对峙、关键对话、重要发现），快速进入矛盾，但不要每一集都是极端冲突
- 经过（80%）：反派持续施压，主角隐忍/被误解，观众情绪被反复拉扯。这是情绪的蓄水池。
- 结果/钩子（10%）：留悬念设卡点，让观众想看下一集。悬念可以是信息差、人物决定、情感转折

【时长与分镜数量】（严格遵守）
- 每集总时长必须达到用户指定的目标时长，不得少于目标时长的80%
- 每个分镜时长2-8秒，通过调整分镜数量来达到目标总时长
- 一般90秒的剧本需要18-25个分镜，60秒需要12-18个分镜
- total_duration字段必须是所有分镜duration之和

【"压-爽"节奏单元】（至少1个循环，允许跨集）
- 至少1个"压-爽"循环，可跨2-3集完成完整的压抑→释放弧线
- 压（情绪低点）：反派施压，主角受辱——压抑时间要长
- 爽（情绪释放）：主角反击、身份揭露——释放瞬间要短而强烈
- 持续压抑后的爆发更有冲击力，不必每集都爽
- 每次反派施压都要比上一次更狠
- 主角反击要干脆利落，一句话或一个动作就完成反转

【冲突升级五层递进】（每集1-2层，自然递进）
第一层：言语冲突——质疑、嘲讽、否定主角价值
第二层：权力碾压——利用身份或地位压制主角
第三层：关系破坏——离间、诬陷、破坏主角的人际关系
第四层：生存威胁——剥夺财产、威胁生计、断绝后路
第五层：终极威胁——生命危险、彻底摧毁（仅在关键节点使用，大多数剧集不达到此层）
要求：冲突逐层递进，不必每集用完五层，1-2层即可。愤怒通过多集累积。

【镜头叙事连续性】（参考爆款短剧的写法）
- 镜头之间靠"动作→反应→下一个动作"的链条来推进，不要每个镜头都是独立事件
- 同一场景内，下一个镜头的画面是上一个镜头动作的结果或角色的反应
- 对话要有来有回：A说→B反应→B说→A反应，不要一个角色长篇大论
- 场景切换：2-3个镜头构成一个场景段落，切换场景时直接在frame_content中写明新地点
- 内心独白（narration）只用在角色特写时配合表情使用，一集不超过3处

【表演和留白】（重要！）
- 允许角色有时间反应、停顿、酝酿情绪，通过1-2秒的反应镜头强化情绪冲击
- 情感递进比信息密度更重要：先让观众感受到，再让观众知道
- 同一个情绪点可以在不同集数中重复强化，这是好的叙事手法
- 对话不一定要句句有功能性，日常化的互动能拉近观众与角色的距离
	- 至少1/3的镜头应该是自然的日常互动，不要每个镜头都在推进冲突

	【避免用力过猛】（关键！）
	- 不是每集都需要耳光、掀桌、下跪。压抑可以通过冷暴力、误解、冷落来实现
	- 允许"什么都没有发生"的镜头：角色走路、喝水、看窗外。这些建立真实感
	- 反派不要每句话都是侮辱。真正的反派魅力在于他/她觉得自己是对的
	- 主角的反击不需要每集都出现。憋屈2-3集再爆发，力量感更强
	- 日常对话示例：\"吃饭了吗\"\"今天怎么样\"\"我有点担心\"——这些建立人物关系

【剧情推进节奏】（自然推进）
- 对白是推进事件的主要手段，不要让旁白喧宾夺主
- 背景信息通过对白带出
- 信息差运用：观众知道而角色不知道（期待感）、角色知道而观众不知道（悬念）

【旁白核心要求】（旁白仅限内心独白）
- 旁白仅用于角色内心独白（OS），展示角色内心真实想法，配合表情特写
- 例：「我不能再相信他了……这次，我要亲手揭穿一切」
- 例：「我发誓，这辈子不会再让任何人欺负我」
- 禁止第三人称解说旁白。OS只能是角色的第一人称内心声音（"我……"），不能是上帝视角描述（"她不知道……" "与此同时……"）
- 禁止回忆旁白，所有背景信息优先通过对白带出。但允许主角通过第一人称OS简短回忆（"上一世，我就是在这里签了那份协议……"）
- 旁白字数灵活，不设硬性目标，如果旁白在某个镜头中显得生硬，直接省略
- 同一镜头中旁白和台词互斥，只能出现一个
- 台词和第一人称OS共同驱动叙事。关键情节通过对白展开，角色内心通过OS揭示。两者互补而非互斥
- 多数镜头应有对话或OS，但允许纯粹的视觉镜头用于情绪建立和过渡

【台词核心要求】（台词是短剧的灵魂）
- 每集总台词量 = 时长秒数 × (5~8)字（例：90秒→450-720字，60秒→300-480字）
- 对话是角色之间的有来有往，至少有一个人说话，每个对话镜头至少20字以上
- 每个对话镜头可以有多句台词（2-4句），不要每个镜头只写一句
- 台词必须简短有力，一句话只抛出一个信息
- 台词口语化、接地气，不要书面化
- 通过对话推进剧情，不要用旁白代替本该用台词表达的内容
- 配角台词也要有信息量，不要写废话

【高频台词模式】（参考使用）

侮辱施压型：
- "就凭你也配？""给我滚！""废物！""不知廉耻！"
- "你也不看看自己什么身份""癞蛤蟆想吃天鹅肉"
- "一个卖鱼女也敢肖想总裁？""你这种人给我提鞋都不配"

反转型：
- "你还不知道吧？""其实……""你以为……其实……"
- "不好意思，这个项目已经被我拿下了"
- "你以为你赢了？好戏才刚刚开始"

身份揭露型：
- "谁说XX和XX退婚了？""这份合同是我让她给你的"
- "以后谁与你为敌就是与XX集团为敌！"
- "她是我的人！""我的人只有我能动，你算什么东西"

情感拉扯型：
- "若有来生，我一定不会放过你们""这一世，我一定不会再负你"
- "我是从死人堆里爬出来的，早已不惧生死"
- "忍耐不是懦弱，而是等待给与对方一击毙命的时机"

霸总护短型：
- "我的人只有我能动，你算什么东西"
- "从今天起，谁敢动她一根头发，就是与整个XX集团为敌"
- "我都没点头，谁敢娶我老婆！"

女主反击型：
- "我后悔没有把酒瓶直接塞到你嘴里"
- "看你这肾气不足的可怜样子"
- "我讲话，你一个小妾，插什么嘴？懂不懂规矩？"

反派嘲讽型：
- "就你这种废物，也配跟我斗？"
- "你以为你能翻身？做梦！"
- "我倒要看看，谁能救得了你！"

【反派塑造要求】（极其重要！反派越可恨，观众越爽）
反派台词要求：
- 反派人物的话越粗俗难听越好，要表现出极端的情绪
- 反派得意时必须主动揭露自己的阴谋（"你还不知道吧？你爸妈是我撞死的！"）——这是核心爽感来源
- 反派嘲讽时要具体，不能泛泛而骂，要针对主角的具体弱点
- 反派的每句台词都要让观众恨得牙痒痒

反派行为要求：
- 反派出手要狠、要绝，不能心慈手软
- 反派恶行要有具体细节（"一脚踹在她脸上"），不抽象概括
- 反派被打脸后可找更强大靠山继续报复

【钩子技法应用】（自然融入，不强制每集全部使用）
开头钩子（前3秒尽量有，但不强求每个镜头都是爆点）：
- 暴力冲突、身份反转、极端情绪、悬念氛围等开场

集末钩子（多数集有，但不强制每集都是扣人心弦）：
A. 关键时刻被打断——谈话聊到关键部分突然停止
B. 人物表情反转——突然露出不可思议/害怕/疑惑表情后卡点
C. 危机即将爆发——正要行动时卡点
D. 身份即将揭露——接近揭露时卡点
E. 新人物/势力出场
F. 情绪高潮卡点
G. 信息差制造悬念——台词"不好了""坏了"

【提示词风格要求】
- 风格定位先行：第一句快速定调整体视觉风格
- 主体描述追求"稳"和"精"：避免空泛形容词，多刻画具体物理特征
- 动作追求"慢"和"连贯"：动词优先+状态描述，写慢不写快
- 镜头语言要明确：每个时间段必须包含景别+运镜+转场
- 每个时间段必须包含画面元素运动描述（主体/环境/背景/特效）
- 约束词保障画面质量：面部特征保持一致、动作流畅连贯、摄像机运动平滑

【景别类型】（每个镜头必须标注）
- 远景：展示宏大场景，环境为主，交代背景
- 全景：展示角色全身及环境关系
- 中景：膝盖以上，日常对话、动作展示
- 近景：胸部以上，聚焦表情、情绪传递
- 特写：面部或局部细节，放大情绪
- 大特写：瞳孔、指尖等极致聚焦
- 主观视角：角色第一人称，增强沉浸感

【运镜/转场类型】（每个镜头必须标注）
基础运镜：
- 固定：稳定画面，对话/静态场景
- 慢推：缓慢靠近主体，强化情绪张力
- 快推：快速靠近，营造紧张感
- 缓拉：缓慢远离，展示环境
- 快拉：快速远离，凸显渺小
- 水平移镜：跟随主体移动
- 弧形移镜：围绕主体移动
- 摇镜：水平/垂直转动展示
- 跟镜：跟随人物行动
- 升降：垂直移动，展示高度变化
- 环绕：360度围绕主体旋转
- 手持：纪实感晃动
转场方式：
- 硬切：直接切换，节奏紧张
- 渐变：淡入淡出，情绪过渡
- 叠化：画面重叠，时间流逝
- 黑场：黑屏过渡，场景转换
- 升格：慢动作强调
- 降格：快动作时间压缩

【视频生成提示词要求】（关键！每个镜头生成一个完整的video_prompt，音频和画面一起生成）
- video_prompt是写给AI视频模型的指令，必须直接描述画面内容和声音内容，不要文学修辞
- 必须把该镜头的dialogue和narration原文完整嵌入，写清楚谁在说什么、用什么声音
- 必须全部使用中文，禁止英文单词
- 禁止用逗号拼接关键词，禁止"8K""高清""masterpiece"等参数词
- 所有角色必须用【角色名】格式，如【苏婉儿】、【顾北辰】

提示词写法规则：
- 写画面：直接描述谁在哪里做什么，什么表情什么动作，镜头怎么动
- 写台词：【角色名】说什么："原文"，用什么语气和音量
- 写内心独白：【角色名】内心声音（OS）："原文"，什么音色什么情绪
- 写音效：具体什么声音从哪来，多大音量
- 不要写文学化的感受描述，写AI能直接生成的视听内容

正确示例（有台词，有景别变化）：
"现代城市夜晚，破旧的出租屋内，昏黄的吊灯微微晃动。【苏婉儿】站在窗边，身穿洗得发白的T恤，头发松散地披在肩上。窗外城市霓虹灯光映在她苍白的脸上。她低头看着手里旧款智能手机的屏幕，手指微微发抖，抿了抿干裂的嘴唇，用低哑压抑的声音缓缓开口说：'我回来了...这一次，不会再让任何人欺负我。'说完眼眶泛红，一滴泪从右眼滑落。镜头从她的中景缓慢推近到面部特写。背景隐约听到远处街道的汽车鸣笛声，窗外雨声渐渐增大。"

正确示例（有内心独白，无台词）：
"夜晚，高层写字楼顶层办公室，落地窗外的城市夜景璀璨。【顾北辰】身穿黑色西装站在窗前，背对镜头，右手无意识地转着左手无名指上的银色戒指。窗外霓虹灯光照在他轮廓分明的侧脸上。镜头从他的背影缓慢环绕移动到侧面中景。此时他嘴唇未动，一个低沉缓慢的内心声音（OS）响起：'我认出来了……这个男人的身份，远比所有人想象的都可怕。'背景安静，只有空调低频的嗡嗡声。"

错误示例（绝对不能这样写）：
"1girl,苏婉儿,出租屋,手机,夜景,8k,高清,冷色调,masterpiece,best quality"

【画面元素运动描述规范】（每个镜头必须包含）
- 主体运动：角色的动作、表情变化
- 环境运动：天空、云、光影、风
- 背景运动：人群、物体、粒子
- 特效运动：火花、雨滴、烟雾

【敏感词合规】
禁止使用：裸体、暴力血腥词汇、真实/真人、明星姓名、品牌名
替换为：素体建模、动作戏、写实风格、同款风格、同风格设计

【伏笔技法】（适当穿插，长线伏笔尤为重要）
一、信物伏笔：道具贯穿全剧，每次接近暴露又收回
二、身份伏笔：各路大佬对主角的态度暗示真实身份
三、闪回伏笔：前世记忆作为伏笔，让主角"预知"阴谋
四、对话伏笔：通过配角对话透露关键信息
五、道具伏笔：手镯、信件、照片等物品反复出现

【反转技法】（关键节点优先使用）
一、身份反转（最核心爽点）：被嘲讽→揭示真实身份→嘲讽者跪地求饶
二、关系反转：仇人实为恩人，盟友实为敌人
三、局势反转：绝境中的反击，将计就计
四、认知反转：观众有上帝视角但剧中人不知

【反差人设】（主角和重要配角优先使用，普通配角可简单化）
1. 表面冷酷无情→实则宠妻狂魔
2. 表面憨厚老实→实则扮猪吃老虎
3. 表面柔弱可怜→实则白切黑
4. 表面花心浪荡→实则深情专一
5. 温文尔雅→内心阴暗心机深沉
6. 飞檐走壁武功高强→憨厚耿直呆头呆脑
7. 咸鱼躺平佛系→能力出众办事效率极高
8. 身娇体弱病弱少年→精明阴险手段毒辣
9. 不近女色清心寡欲→恋爱脑痴情一片
10. 心狠手辣暴怒狂虐→撒娇黏人铁憨憨
11. 心直口快爱怼人→认怂求放过胆小鬼
12. 杀伐果断冷酷无情→硬汉娇夫小奶狗
13. 运筹帷幄执掌大权→内心脆弱可怜无助
14. 憨厚耿直好欺负→无比精明扮猪吃老虎
15. 离经叛道野蛮生长→人间清醒专治不服
16. 睚眦必报武力爆表→内心柔弱小哭包
17. 不学无术纨绔子弟→深情专一博学多才
18. 柔弱不能自理小哭包→白切黑疯批毁天灭地
19. 高岭之花冷清大女主→恋爱脑粘人小妖精
20. 茶言茶语又坏又作→人间清醒聪明机敏

【反派七类阴险套路】（根据剧情需要灵活选用）
一、强拆CP：抢主角女神、利用性格缺陷制造矛盾、炫耀成就让主角自卑
二、扮猪吃老虎：装可怜引起同情、装正义搜集黑历史、伪装跟班伺机出手
三、冤枉陷害：暗中算计、散播谣言、陷害入狱、假扮盟友
四、利用算计：利用仁慈之心、利用对亲人的感情、利用弱点
五、麻烦制造机：利用恋爱/亲人/缺点/仇恨制造麻烦
六、麻烦危机：制造障碍、偷盗财物、假扮朋友、利用家族/软肋
七、反复背叛：在最困难时扮演救世主再背叛、相处成朋友后密谋背叛

【危机感塑造】（关键节点优先使用）
一、信息差：主角身边的人不知道主角早就帮自己解决了麻烦，自己去找反派却被威胁
二、时间锁：给任务设定时间限制，利用时间压力构造紧迫感（最后一秒钟营救）
三、生死局：主角陷入危机，一旦无法解决就会死，最常见的是赌局

【八种剧情写法】（根据题材灵活选用）
1. 侮辱和背叛：被男友、闺蜜、亲近的人侮辱、背叛
2. 误会：被男主无脑误会
3. 暴力对待：身体暴力、情感暴力
4. 肢体冲突、情感冲突：虐身虐心
5. 言语攻击：配角对主角的言语攻击
6. 不信守承诺：人物出尔反尔
7. 童年阴影：某种行为是童年遭受阴影导致的
8. 欺诈：观众有上帝视角，知道人物被欺诈，而剧中人物不知道

【六大矛盾来源】（根据剧情需要选用）
1. 男主和女主的矛盾
2. 男主和女配的矛盾
3. 女主和女配的矛盾
4. 女主和男配的矛盾
5. 男主和男配的矛盾
6. 角色与自身价值观的冲突

【爽感来源】（适当融入剧情）
身份碾压、能力碾压、财富碾压、人脉碾压、情感碾压、绝境反杀、扮猪吃老虎、重生改变命运、大佬对小人物恭敬、聚会遭歧视后大人物对主角点头哈腰、将计就计、反转打脸、以牙还牙、身份揭露震惊全场

【钩子类型标记】（严格克制：一集最多4个标记，其余全部null。不要每集涵盖所有钩子类型）
一集通常只有2-4个镜头需要标注hook_type，其余全部用null。仅以下情况标注：
- "hook": 仅标记第1个镜头（开场爆点/黄金3秒）
- "cliffhanger": 仅标记最后1个镜头（结尾悬念）
- "foreshadowing": 仅标记明确埋下后续集才揭晓的伏笔
- "turning_point": 仅标记剧情方向的重大转折（一整集最多1-2个）
- "emotional_peak": 仅标记全集的情绪最高点
- "revelation": 仅标记身份/真相关键揭露时刻
- "conflict": 仅标记冲突爆发的顶点
- null: 普通镜头（绝大多数镜头填null）

普通冲突、普通对话、情绪过渡、场景切换、角色出场等，一律标记为null。不要因为"有冲突"就标conflict，不要因为"有情感"就标emotional_peak。
不要在每一个有情绪变化的镜头上标hook_type。一集最多用2-3种钩子类型，绝对不能7种都用。

【输出格式】
【重要】请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记。

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
      "dialogue": "台词（含情绪标注，每个镜头可包含多句对话，用换行分隔不同角色的台词）",
      "narration": "旁白/内心独白（仅限内心独白，台词与旁白在同一镜头中互斥，不能同时出现）",
      "bgm_suggestion": "背景音乐建议",
      "duration": 3.0,
      "video_prompt": "视频生成提示词（写给AI视频模型的指令，直接描述画面和声音。格式：【角色名】做什么动作/说什么话"原文"+语气+音量/内心声音OS"原文"+音色/具体音效/镜头运动。禁止文学修辞，禁止逗号拼接关键词）",
      "color_palette": "色调建议（暖色调/冷色调/高饱和/低饱和/黑白等）",
      "hook_type": "钩子类型（hook/cliffhanger/foreshadowing/turning_point/emotional_peak/revelation/conflict/null）",
      "hook_detail": "钩子详细分析（如果是钩子镜头，说明为什么这里是爆点/悬念/伏笔）",
      "notes": "制作备注"
    }
  ],
  "total_duration": 90
}"""

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

【提示词要求】
必须全部使用中文，禁止出现任何英文单词或短语。使用自然语言段落描述画面，像导演给摄影师的口述指令。包含：风格定位、人物外貌细节、姿态动作、场景环境、光影效果。不要使用逗号拼接关键词，不要使用"8k""高清""masterpiece""best quality"等中英文参数词。

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

请生成JSON格式的角色设计卡。
【重要】请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记。

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
    "front_view": "三视图 — 正面：全身提示词（风格+人物完整外貌+服装细节+姿态+光影+质量词+负面提示词）",
    "side_view": "三视图 — 侧面：全身提示词",
    "back_view": "三视图 — 背面：全身提示词"
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
"""

SCENE_DESIGN_PROMPT = """你是一个AI漫剧场景设计专家，精通场景空间深度和氛围营造。

场景信息：
名称: {name}
描述: {description}
氛围: {atmosphere}

【场景设计三维度】
1. 定位：场景类型（城市/自然/室内/科幻/古风等）
2. 时间/天气：时刻+光线/天气
3. 交互细节：飘落樱花/全息投影/地面倒影等

【提示词要求】
必须全部使用中文，禁止出现任何英文单词或短语。使用自然语言段落描述场景画面，像导演给美术指导的场景描述。包含：风格定位、场景空间描述、时间天气、光影氛围、交互细节。不要使用逗号拼接关键词，不要使用"8k""高清""masterpiece"等中英文参数词。

【光影类型】
逆光、侧光、顶光、伦勃朗光、剪影、轮廓光、体积光、丁达尔效应

【色调类型】
暖色调、冷色调、高饱和、低饱和、黑白、赛博朋克、复古胶片

请生成JSON格式的场景设计卡。
【重要】请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记。

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
"""

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

请按以下JSON格式输出，每个字段都要尽量详细。
【重要】请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记。

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
          "duration": 3.0,
          "video_prompt": "视频生成提示词（写给AI视频模型的指令，直接描述画面和声音。【角色名】说"原文"+语气/内心声音OS"原文"+音色/具体音效/镜头运动）",
          "hook_type": "钩子类型",
          "hook_detail": "钩子分析"
        }}
      ]
    }}
  ]
}}
"""


class ScriptGenerator:
    """Multi-phase script generator with knowledge base management."""

    def __init__(self):
        self._active_tasks: dict[str, ScriptResponse] = {}
        self._completed_scripts: dict[str, dict] = {}

    async def start_generation(self, request: ScriptRequest) -> str:
        """Start async script generation. Returns task ID."""
        task_id = str(uuid.uuid4())[:8]
        project_id = f"project_{task_id}"

        self._active_tasks[task_id] = ScriptResponse(
            id=task_id,
            status="generating",
            progress=0.0,
            total_episodes=request.episode_count,
            started_at=datetime.now().isoformat(),
        )

        asyncio.create_task(self._generate_script(task_id, project_id, request))
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[ScriptResponse]:
        return self._active_tasks.get(task_id)

    def list_all_tasks(self) -> list[dict]:
        """Return all tasks: active (generating) + completed. For script list UI."""
        tasks = []
        for task_id, task in self._active_tasks.items():
            script_data = task.script.model_dump() if task.script else None
            # Also check _completed_scripts for scripts that finished but were polled
            completed = self._completed_scripts.get(task_id)
            if completed and not script_data:
                script_data = completed
            tasks.append({
                "id": task_id,
                "title": script_data.get("title", "") if script_data else task.current_phase or "正在生成...",
                "genre": script_data.get("genre", "") if script_data else "",
                "status": task.status,
                "progress": task.progress,
                "current_phase": task.current_phase,
                "created_at": script_data.get("created_at", "") if script_data else "",
            })
        # Add completed scripts that are no longer in _active_tasks
        for task_id, script in self._completed_scripts.items():
            if task_id not in self._active_tasks:
                tasks.append({
                    "id": task_id,
                    "title": script.get("title", ""),
                    "genre": script.get("genre", ""),
                    "status": "completed",
                    "progress": 100.0,
                    "current_phase": "",
                    "created_at": script.get("created_at", ""),
                })
        return tasks

    def get_completed_script(self, task_id: str) -> Optional[dict]:
        """Get a completed script by ID, even if no longer in active tasks."""
        return self._completed_scripts.get(task_id)

    async def _generate_script(self, task_id: str, project_id: str, request: ScriptRequest):
        """Full script generation pipeline."""
        kb = KnowledgeBase(project_id)

        try:
            # Phase 1: Story Planning
            self._active_tasks[task_id].current_phase = "正在策划故事"
            self._active_tasks[task_id].progress = 5.0
            story_plan = await self._plan_story(request)
            if not story_plan:
                raise Exception("故事策划失败，请检查AI配置")

            # Set the script title early so UI can display it
            self._active_tasks[task_id].title = story_plan.get("title", request.topic)

            # Initialize knowledge base
            self._init_knowledge_base(kb, story_plan)
            self._active_tasks[task_id].progress = 15.0

            # Phase 2: Generate character designs
            self._active_tasks[task_id].current_phase = "正在设计角色"
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
                    three_view_prompt=s(char_data.get("three_view_prompt", char_data.get("ai_prompt", char_data.get("ai_prompt_cn", "")))),
                )
                characters.append(char)

            self._active_tasks[task_id].progress = 20.0

            # Phase 3: Generate each episode
            episodes = []
            for ep_num in range(1, request.episode_count + 1):
                self._active_tasks[task_id].current_episode = ep_num
                self._active_tasks[task_id].current_phase = f"正在创作第 {ep_num}/{request.episode_count} 集"
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
            self._active_tasks[task_id].current_phase = "正在组装最终剧本"
            script = Script(
                id=task_id,
                title=story_plan.get("title", request.topic),
                genre=request.genre,
                logline=story_plan.get("logline", ""),
                synopsis=story_plan.get("synopsis", ""),
                characters=characters,
                episodes=episodes,
                scenes=story_plan.get("scenes", []),
                props=story_plan.get("props", []),
                theme=story_plan.get("theme", ""),
                emotional_tone=story_plan.get("emotional_tone", ""),
                target_audience=request.target_audience,
                style=request.style,
            )

            self._active_tasks[task_id].script = script
            self._active_tasks[task_id].status = "completed"
            self._active_tasks[task_id].progress = 100.0

            # Store completed script persistently so it's available even if abandoned by polling
            self._completed_scripts[task_id] = script.model_dump()

            # Persist to disk cache immediately upon completion
            try:
                from app.api.scripts import save_script_to_disk_cache, _script_store
                _script_store[task_id] = script.model_dump()
                save_script_to_disk_cache()
            except Exception as e:
                logger.warning(f"Failed to persist script {task_id} to disk cache: {e}")

        except Exception as e:
            logger.error(f"Script generation failed: {e}", exc_info=True)
            self._active_tasks[task_id].status = "failed"
            self._active_tasks[task_id].error = str(e)

    async def _plan_story(self, request: ScriptRequest) -> dict:
        """Phase 1: Generate overall story plan."""
        logger.info(f"Phase 1: Starting story planning for topic: {request.topic}")
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
题材: {request.genre}
集数: {request.episode_count}集
每集时长: {request.episode_duration}秒
目标受众: {request.target_audience}
风格: {request.style}
特殊要求: {request.special_requirements}
{trend_context}

请严格按照系统提示中的JSON格式输出完整方案。特别注意：
1. 故事必须原创，不要直接套用热点标题或简介
2. 每个角色都要有完整的三视图AI绘图提示词
3. 每个场景都要有场景提示词（自然语言段落描述）和多个变体
4. 重要道具也要有提示词（自然语言段落描述）
5. 表情和动作的提示词要详细可用
6. 【最重要】必须设计一个贯穿全剧的核心悬念钩子（core_mystery），在第1集开头就展示出来，但答案要到至少第5集之后才逐步揭晓。这个悬念是观众持续观看的核心动力。
7. 所有提示词使用自然语言段落描述，不要使用逗号拼接关键词"""

        messages = [
            {"role": "system", "content": STORY_PLANNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = await self._call_and_extract_json(messages, temperature=0.9, max_tokens=8192)
        if not result:
            logger.error("Story planning returned empty JSON after retries")
        else:
            logger.info(f"Phase 1: Story plan extracted, title={result.get('title', '?')}")
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
题材: {request.genre}
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
2. 每个分镜都有完整的video_prompt（必须包含该镜头的所有对话和独白原文，音频画面一起生成）
3. 台词口语化、有网感，台词量{request.episode_duration * 5}-{request.episode_duration * 8}字（根据{request.episode_duration}秒时长计算）
4. 旁白仅限内心独白，台词和旁白同一镜头互斥，字数灵活
5. 结尾是悬念
6. 与前几集保持剧情连贯
7. video_prompt使用自然语言段落描述，不要使用逗号拼接关键词
8. 如果知识库上下文中包含"本集必须包含的原著钩子"，在对应分镜标记hook_type和hook_detail
9. total_duration必须等于所有分镜duration之和，且必须达到{request.episode_duration}秒的目标时长
10. 叙事节奏自然，允许角色反应和情绪留白"""

        messages = [
            {"role": "system", "content": EPISODE_GENERATOR_PROMPT},
            {"role": "user", "content": prompt},
        ]

        data = await self._call_and_extract_json(messages, temperature=0.85, max_tokens=8192)

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
                narration=s.get("narration") or "",
                duration=s.get("duration") or 3.0,
                # video_prompt replaces old ai_prompt; backward compatible
                video_prompt=s.get("video_prompt") or s.get("ai_prompt") or s.get("ai_prompt_cn") or "",
                notes=s.get("notes") or "",
                hook_type=s.get("hook_type") if s.get("hook_type") and s.get("hook_type") != "null" else None,
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

        # Strategy 1: Find outermost { } by counting braces (primary — prompts require bare JSON)
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

        # Strategy 2: Extract from markdown code block (fallback for models that add ```json)
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', text)
        if json_match:
            result = self._try_parse_json(json_match.group(1))
            if result:
                return result

        # Strategy 3: Regex fallback (greedy)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = self._try_parse_json(json_match.group(0))
            if result:
                return result

        logger.warning(f"Failed to extract JSON from response (length={len(text)}): {text[:200]}...")
        return {}

    def _try_parse_json(self, text: str) -> dict:
        """Try to parse JSON with common fixups for LLM output quirks."""
        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fix common issues from LLM output
        fixed = text
        # Remove single-line comments
        fixed = re.sub(r'//.*?\n', '\n', fixed)
        # Remove trailing commas before } or ]
        fixed = re.sub(r',\s*([\]}])', r'\1', fixed)

        # Fix unescaped backslashes inside JSON strings (common LLM error)
        # Only fix \ that are NOT already part of a valid escape sequence
        # Valid escapes: \\, \", \/, \b, \f, \n, \r, \t, \uXXXX
        result = []
        in_str = False
        esc = False
        i = 0
        while i < len(fixed):
            ch = fixed[i]
            if esc:
                result.append(ch)
                esc = False
                i += 1
                continue
            if ch == '\\' and in_str:
                # Check if next char forms a valid escape
                if i + 1 < len(fixed) and fixed[i + 1] in '"\\/bfnrtu':
                    result.append(ch)  # valid escape, keep as-is
                else:
                    result.append('\\\\')  # double the backslash
                    i += 1
                    continue
            elif ch == '"':
                in_str = not in_str
                result.append(ch)
                i += 1
                continue
            elif in_str and ch == '\n':
                result.append('\\n')
                i += 1
                continue
            elif in_str and ch == '\t':
                result.append('\\t')
                i += 1
                continue
            elif in_str and ch == '\r':
                result.append('\\r')
                i += 1
                continue
            elif in_str and ord(ch) < 0x20:
                # Control character in string → escape it
                result.append(f'\\u{ord(ch):04x}')
                i += 1
                continue
            result.append(ch)
            i += 1
        fixed = ''.join(result)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Last resort: try to fix truncated JSON by closing open brackets in stack order
        try:
            bracket_stack = []  # tracks opening order: '{' or '['
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
                if ch in '{[':
                    bracket_stack.append(ch)
                elif ch == '}':
                    if bracket_stack and bracket_stack[-1] == '{':
                        bracket_stack.pop()
                elif ch == ']':
                    if bracket_stack and bracket_stack[-1] == '[':
                        bracket_stack.pop()

            if bracket_stack:
                if in_string:
                    fixed += '"'
                # Pop from end (innermost first) and add corresponding closers
                closing = ''
                for b in reversed(bracket_stack):
                    closing += '}' if b == '{' else ']'
                fixed += closing
                return json.loads(fixed)
        except (json.JSONDecodeError, Exception):
            pass

        return {}

    async def _call_and_extract_json(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 8192, max_retries: int = 5) -> dict:
        """Call LLM and extract JSON, retrying if parsing fails."""
        last_response = ""
        for attempt in range(max_retries + 1):
            response = await ai_client.chat(messages, temperature=temperature, max_tokens=max_tokens)
            last_response = response
            result = self._extract_json(response)
            if result:
                return result

            logger.warning(f"JSON extraction failed on attempt {attempt + 1}/{max_retries + 1}, retrying...")
            # Add the failed response and a correction prompt for retry
            messages = messages + [
                {"role": "assistant", "content": response},
                {"role": "user", "content": "你的输出无法解析为JSON。请直接输出纯JSON文本，不要用```json代码块包裹，不要添加任何markdown格式标记，不要包含任何解释文字。重新输出："},
            ]

        logger.error(f"JSON extraction failed after {max_retries + 1} attempts. Last response: {last_response[:500]}")
        return {}

    async def start_novel_adaptation(self, text: str, episode_count: int = 8, genre: str = "重生",
                                      style: str = "古风", chapters: list[str] | None = None) -> str:
        """Start async novel adaptation. Returns task ID.

        Args:
            text: Full novel text (for story plan context)
            chapters: Pre-parsed chapter texts (from DOCX headings or regex). If None,
                      _split_chapters will be called on the text.
        """
        task_id = str(uuid.uuid4())[:8]
        self._active_tasks[task_id] = ScriptResponse(
            id=task_id,
            status="generating",
            progress=0.0,
            total_episodes=episode_count,
            started_at=datetime.now().isoformat(),
        )
        asyncio.create_task(self._adapt_novel_async(task_id, text, episode_count, genre, style, chapters))
        return task_id

    async def _adapt_novel_async(self, task_id: str, novel_content: str, episode_count: int,
                                  genre: str, style: str, chapters: list[str] | None = None):
        """Background wrapper that updates task status."""
        try:
            result = await self.adapt_novel(novel_content, episode_count, genre, style,
                                            task_id=task_id, chapters=chapters)
            self._active_tasks[task_id].script = Script(
                id=task_id,
                title=result.get("title", ""),
                genre=result.get("genre", ""),
                logline=result.get("logline", ""),
                synopsis=result.get("synopsis", ""),
                characters=[Character(
                    name=str(c.get("name", "") or ""),
                    age=str(c.get("age", "") or ""),
                    identity=str(c.get("identity", "") or ""),
                    personality=str(c.get("personality", "") or ""),
                    appearance=str(c.get("appearance", "") or ""),
                    clothing=str(c.get("clothing", "") or ""),
                    signature_element=str(c.get("signature_element", "") or ""),
                    arc=str(c.get("arc", "") or ""),
                    relationships=c.get("relationships", {}) if isinstance(c.get("relationships"), dict) else {},
                    three_view_prompt=str(c.get("three_view_prompt", "") or ""),
                ) for c in result.get("characters", [])],
                episodes=[Episode(**e) for e in result.get("episodes", [])],
                scenes=result.get("scenes", []),
                props=result.get("props", []),
                theme=result.get("theme", ""),
                emotional_tone=result.get("emotional_tone", ""),
                style=result.get("style", style),
            )
            self._active_tasks[task_id].status = "completed"
            self._active_tasks[task_id].progress = 100.0
            self._completed_scripts[task_id] = result
            # Persist to disk cache
            try:
                from app.api.scripts import save_script_to_disk_cache, _script_store
                _script_store[task_id] = result
                save_script_to_disk_cache()
            except Exception as e:
                logger.warning(f"Failed to persist adapted script {task_id}: {e}")
        except Exception as e:
            logger.error(f"Novel adaptation failed: {e}", exc_info=True)
            self._active_tasks[task_id].status = "failed"
            self._active_tasks[task_id].error = str(e)

    async def adapt_novel(self, novel_content: str, episode_count: int = 8, genre: str = "重生",
                           style: str = "古风", task_id: str = "", chapters: list[str] | None = None) -> dict:
        """Convert a novel into a drama script — optimized pipeline with optional progress feedback.

        Optimizations:
        1. Merged overview extraction into story plan (saves 1 LLM call)
        2. Lowered batch-summary threshold (5+ ch / 10k+ chars → all novels get summaries)
        3. Skip _enhance_asset_designs when story plan already has complete prompts
        4. Parallel episode generation via asyncio.gather
        5. KB context truncation after all sections appended (prevents overflow)
        6. Single context format for all novel sizes
        7. Async progress feedback via _active_tasks (when task_id provided)
        """
        def _update_progress(progress: float, phase: str, title: str = ""):
            if task_id and task_id in self._active_tasks:
                self._active_tasks[task_id].progress = progress
                self._active_tasks[task_id].current_phase = phase
                if title:
                    self._active_tasks[task_id].title = title

        chapters_result = self._split_chapters(novel_content, docx_chapters=chapters)
        # If regex/double-newline only gave us equal-length chunks (last fallback), try intelligent detection
        if chapters is None and len(chapters_result) < 3:
            logger.info("Regex split found too few chapters, trying intelligent detection...")
            chapters_result = await self._split_chapters_intelligent(novel_content)
        total_chars = len(novel_content)
        chapters = chapters_result
        if chapters is not None:
            logger.info(f"Using pre-parsed chapters (DOCX)")
        logger.info(f"Novel split into {len(chapters)} chapters, total {total_chars} chars")

        # Phase 1: Summarize all chapters (lower threshold → better coverage)
        _update_progress(5.0, "正在拆分章节并生成摘要...")
        chapter_summaries = []
        chapter_hooks = []
        if total_chars > 10000 or len(chapters) > 5:
            # Adaptive batch size: keep total LLM calls reasonable (<~20 batches)
            total_ch = len(chapters)
            if total_ch <= 30:
                batch_size = 5
            elif total_ch <= 80:
                batch_size = 8
            else:
                batch_size = max(10, total_ch // 15)  # cap at ~15 batches for very long novels
            logger.info(f"Batch-summarizing {total_ch} chapters (batch_size={batch_size})...")
            chapter_summaries, chapter_hooks = await self._batch_summarize_and_extract_hooks(chapters, batch_size=batch_size)
            logger.info(f"Summarized {len(chapter_summaries)} chapters, extracted {len(chapter_hooks)} hooks")
        else:
            for i, ch in enumerate(chapters):
                chapter_summaries.append(f"第{i+1}章: {ch[:300]}")

        # Build novel context from chapter summaries (unified format for all novel sizes)
        # Cap summaries for the story plan to avoid LLM context overflow
        MAX_SUMMARIES_FOR_PLAN = 60
        plan_summaries = chapter_summaries
        if len(chapter_summaries) > MAX_SUMMARIES_FOR_PLAN:
            step = max(1, len(chapter_summaries) // MAX_SUMMARIES_FOR_PLAN)
            plan_summaries = chapter_summaries[::step][:MAX_SUMMARIES_FOR_PLAN]
            logger.info(f"Chapter summaries for story plan capped: {len(chapter_summaries)} → {len(plan_summaries)}")

        novel_context = f"""【原著改编信息】
题材: {genre}
风格: {style}
总字数: {total_chars}
总章数: {len(chapters)}

【章节摘要】（共{len(chapter_summaries)}章，展示{len(plan_summaries)}章）
{chr(10).join(plan_summaries)}"""

        # Append hook index
        if chapter_hooks:
            type_labels = {
                "hook": "开头爆点", "cliffhanger": "章末悬念", "foreshadowing": "伏笔",
                "turning_point": "情节转折", "emotional_peak": "情感高潮",
                "revelation": "真相揭露", "conflict": "冲突爆发",
            }
            hooks_lines = []
            for h in chapter_hooks:
                label = type_labels.get(h["type"], h["type"])
                hooks_lines.append(f"第{h['chapter']}章: {label} - {h['description']}")
            novel_context += f"\n\n【原著钩子索引】（改编时必须保留这些关键钩子）\n{chr(10).join(hooks_lines)}"

        # Append key chapter excerpts for richer detail
        key_chapters_text = self._get_key_chapters_text(chapters, episode_count)
        if key_chapters_text:
            novel_context += f"\n\n【关键章节原文】\n{key_chapters_text}"

        # Phase 2: Generate story plan (merged overview + plan in one LLM call)
        _update_progress(10.0, "正在分析原著并生成故事策划...")
        logger.info("Generating story plan from novel...")
        story_plan = await self._adapt_story_plan(novel_context, genre, style, episode_count)
        if not story_plan:
            logger.error("Story plan generation failed, falling back to single-shot adaptation")
            return await self._adapt_novel_single_shot(novel_context)
        _update_progress(20.0, "故事策划完成", title=story_plan.get("title", ""))

        # Phase 3: Skip asset enhancement if story plan already has complete prompts
        chars = story_plan.get("characters", [])
        scenes = story_plan.get("scenes", [])
        chars_complete = len(chars) > 0 and all(
            c.get("three_view_prompt") and c.get("portrait_prompt") for c in chars
        )
        scenes_complete = len(scenes) > 0 and all(
            s.get("scene_prompt") for s in scenes
        )
        if chars_complete and scenes_complete:
            logger.info("Story plan already has complete asset prompts, skipping asset enhancement")
            enhanced_plan = story_plan
        else:
            _update_progress(20.0, "正在优化角色与场景设计...")
            logger.info("Enhancing incomplete asset designs...")
            enhanced_plan = await self._enhance_asset_designs(story_plan)

        # Phase 4: Initialize KnowledgeBase for cross-episode consistency
        kb = KnowledgeBase(f"novel_adapt_{uuid.uuid4().hex[:8]}")
        self._init_knowledge_base(kb, enhanced_plan)
        ch_per_ep = len(chapters) / episode_count if episode_count > 0 else 1

        # Phase 5: Generate all episodes in parallel
        _update_progress(20.0, f"正在并行创作 {episode_count} 集剧本...")
        logger.info(f"Generating {episode_count} episodes in parallel...")

        async def generate_one(ep_num: int):
            ep_plan = {}
            ep_plans = enhanced_plan.get("episode_plan", [])
            if ep_num <= len(ep_plans):
                ep_plan = ep_plans[ep_num - 1]

            context = kb.get_context_for_episode(ep_num)

            # Append chapter summaries for this episode's range
            if chapter_summaries:
                total_ch = len(chapters)
                if ch_per_ep < 1:
                    # Short novel → many episodes: all chapters map to every episode.
                    # Give each episode ALL chapter summaries (there are few) so the
                    # LLM can draw from the full source material.
                    ep_chapter_summaries = chapter_summaries
                    ep_chapter_label = "原著全部章节"
                elif ch_per_ep > len(chapter_summaries) / 2:
                    # Long novel → few episodes: too many chapters per episode.
                    # Select evenly distributed key chapters instead of a huge range
                    # that would be immediately truncated.
                    total_summaries = len(chapter_summaries)
                    max_per_ep = min(15, total_summaries)
                    step = max(1, total_summaries // max_per_ep)
                    start_idx = min((ep_num - 1) * step, total_summaries - 1)
                    ep_chapter_summaries = chapter_summaries[start_idx::step][:max_per_ep]
                    ep_chapter_label = f"原著关键章节（共{total_summaries}章，采样{len(ep_chapter_summaries)}章）"
                else:
                    ch_start = int((ep_num - 1) * ch_per_ep)
                    ch_end = int(ep_num * ch_per_ep)
                    ep_chapter_summaries = chapter_summaries[ch_start:ch_end]
                    ep_chapter_label = "本集对应原著章节"

                if ep_chapter_summaries:
                    context += f"\n\n## {ep_chapter_label}\n{chr(10).join(ep_chapter_summaries)}"

                # Hooks: for short→many, all hooks; for long→few, sampled; normal: range-based
                if ch_per_ep < 1:
                    ep_hooks = chapter_hooks
                elif ch_per_ep > len(chapter_summaries) / 2:
                    ep_hooks = chapter_hooks[start_idx::step][:max_per_ep * 3]
                else:
                    ch_start = int((ep_num - 1) * ch_per_ep)
                    ch_end = int(ep_num * ch_per_ep)
                    ep_hooks = [h for h in chapter_hooks if ch_start < h["chapter"] <= ch_end]

                if ep_hooks:
                    type_labels_inner = {
                        "hook": "开头爆点", "cliffhanger": "章末悬念", "foreshadowing": "伏笔",
                        "turning_point": "情节转折", "emotional_peak": "情感高潮",
                        "revelation": "真相揭露", "conflict": "冲突爆发",
                    }
                    hooks_lines = []
                    for h in ep_hooks[:20]:
                        label = type_labels_inner.get(h["type"], h["type"])
                        hooks_lines.append(f"- {label}: {h['description']}")
                    context += f"\n\n## 本集必须包含的原著钩子\n{chr(10).join(hooks_lines)}"

            # Truncate AFTER all context sections are appended
            max_ctx = 6000
            if len(context) > max_ctx:
                context = context[:max_ctx] + "\n\n[上下文已截断...]"

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
                return ep_num, episode, None
            except Exception as e:
                logger.error(f"Episode {ep_num} generation failed: {e}")
                return ep_num, None, str(e)

        results = await asyncio.gather(*[generate_one(n) for n in range(1, episode_count + 1)])

        _update_progress(95.0, "正在组装最终剧本...")

        # Phase 6: Save episodes to KB sequentially and assemble
        episodes = []
        for ep_num, episode, error in sorted(results, key=lambda x: x[0]):
            if episode:
                episodes.append(episode.model_dump())
                kb.save_episode(episode)
                kb.extract_entities_from_episode(episode)
            else:
                episodes.append({
                    "episode_number": ep_num,
                    "title": f"第{ep_num}集",
                    "summary": f"生成失败: {error[:100]}" if error else "生成失败",
                    "shots": [],
                })

        result = {
            "title": enhanced_plan.get("title", "未命名剧本"),
            "genre": genre,
            "logline": enhanced_plan.get("logline", ""),
            "synopsis": enhanced_plan.get("synopsis", ""),
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

    async def _batch_summarize_and_extract_hooks(self, chapters: list[str], batch_size: int = 5) -> tuple[list[str], list[dict]]:
        """Summarize chapters and extract hooks in batches. Returns (summaries, hooks).

        For extremely long novels (>150 chapters), samples evenly to cap LLM calls.
        """
        all_summaries = []
        all_hooks = []
        total = len(chapters)

        # Cap: for 150+ chapters, sample evenly instead of summarizing everything
        MAX_BATCHES = 20
        if total // batch_size > MAX_BATCHES:
            step = max(1, total // (MAX_BATCHES * batch_size))
            chapters = chapters[::step]
            logger.info(f"Very long novel ({total} chapters): sampled to {len(chapters)} before batch summary")
            total = len(chapters)

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = chapters[batch_start:batch_end]

            # Build batch prompt
            batch_text = ""
            for i, ch in enumerate(batch):
                ch_num = batch_start + i + 1
                ch_content = ch[:3000] if len(ch) > 3000 else ch
                batch_text += f"\n--- 第{ch_num}章 ---\n{ch_content}\n"

            prompt = f"""请为以下每一章完成两个任务：
1. 生成简短摘要（50-100字），保留关键人物、事件、冲突和转折点
2. 提取该章中的钩子元素（悬念、爆点、反转、伏笔、情感高潮等）

钩子类型说明：
- hook: 开头爆点，3秒内抓住观众
- cliffhanger: 章末悬念，让人想看下一章
- foreshadowing: 伏笔，暗示后续剧情
- turning_point: 情节转折，局势逆转
- emotional_peak: 情感高潮，最煽情/最爽的时刻
- revelation: 真相揭露，秘密曝光
- conflict: 核心冲突爆发

{batch_text}

请直接输出纯JSON数组，格式如下：
[
  {{
    "chapter": {batch_start + 1},
    "summary": "第{batch_start + 1}章摘要",
    "hooks": [
      {{"type": "cliffhanger", "description": "钩子描述", "position": "end"}},
      {{"type": "foreshadowing", "description": "伏笔描述", "position": "middle"}}
    ]
  }}
]

每章提取0-3个最有价值的钩子。position为start/middle/end。如果没有明显钩子，hooks数组为空。"""

            try:
                result = await self._call_and_extract_json([
                    {"role": "system", "content": "你是一个小说分析专家，擅长提取章节核心信息和钩子元素。请直接输出纯JSON数组。"},
                    {"role": "user", "content": prompt},
                ], temperature=0.3, max_tokens=3000)

                items = []
                if isinstance(result, list):
                    items = result
                elif isinstance(result, dict) and "chapters" in result:
                    items = result["chapters"]

                if items:
                    for item in items:
                        ch_num = item.get("chapter", 0)
                        summary = item.get("summary", "")
                        if summary:
                            all_summaries.append(f"第{ch_num}章: {summary}")
                        for hook in item.get("hooks", []):
                            hook_type = hook.get("type", "")
                            desc = hook.get("description", "")
                            position = hook.get("position", "end")
                            if hook_type and desc:
                                all_hooks.append({
                                    "chapter": ch_num,
                                    "type": hook_type,
                                    "description": desc,
                                    "position": position,
                                })
                else:
                    for i, ch in enumerate(batch):
                        ch_num = batch_start + i + 1
                        all_summaries.append(f"第{ch_num}章: {ch[:200]}...")

                logger.info(f"Summarized chapters {batch_start + 1}-{batch_end}/{total}")

            except Exception as e:
                logger.error(f"Batch summarization failed for chapters {batch_start + 1}-{batch_end}: {e}")
                for i, ch in enumerate(batch):
                    ch_num = batch_start + i + 1
                    all_summaries.append(f"第{ch_num}章: {ch[:200]}...")

        return all_summaries, all_hooks

    def _get_key_chapters_text(self, chapters: list[str], episode_count: int) -> str:
        """Extract full text of key chapters: first, last, and climax points."""
        key_indices = set()
        total = len(chapters)

        # First 2 chapters
        key_indices.update(range(min(2, total)))

        # Last 2 chapters
        key_indices.update(range(max(0, total - 2), total))

        # Climax points (roughly at 25%, 50%, 75% of the story)
        for pct in [0.25, 0.5, 0.75]:
            idx = int(total * pct)
            key_indices.add(idx)

        # Chapter-to-episode boundaries
        if episode_count > 0:
            ch_per_ep = total / episode_count
            for ep in range(episode_count):
                idx = int(ep * ch_per_ep)
                key_indices.add(idx)

        key_indices = sorted(i for i in key_indices if 0 <= i < total)

        parts = []
        for idx in key_indices:
            ch_text = chapters[idx][:2000]
            parts.append(f"--- 第{idx + 1}章 ---\n{ch_text}")

        return "\n\n".join(parts)[:15000]

    async def _adapt_story_plan(self, novel_context: str, genre: str, style: str, episode_count: int) -> dict:
        """Generate story plan from novel content."""
        prompt = f"""请基于以下小说内容，生成完整的短剧改编策划方案。

{novel_context}

要求：
- 改编为{episode_count}集短剧
- 保留原著核心冲突和情感线，但要重新结构化为短剧节奏
- 为每个角色生成完整设定（包含三视图提示词）
- 为每个场景生成场景提示词和变体
- 为重要道具生成提示词
- 生成每集的计划大纲

请严格按照系统提示中的JSON格式输出。"""

        messages = [
            {"role": "system", "content": STORY_PLANNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await self._call_and_extract_json(messages, temperature=0.8, max_tokens=8192)

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

        design = await self._call_and_extract_json([
            {"role": "system", "content": "你是一个AI漫剧角色设计专家。请根据角色信息生成完整的设计卡。"},
            {"role": "user", "content": prompt},
        ], temperature=0.7, max_tokens=4096)

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

        design = await self._call_and_extract_json([
            {"role": "system", "content": "你是一个AI漫剧场景设计专家。请根据场景信息生成完整的设计卡。"},
            {"role": "user", "content": prompt},
        ], temperature=0.7, max_tokens=4096)

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

        return await self._call_and_extract_json(messages, temperature=0.8, max_tokens=8192)

    @staticmethod
    def parse_docx(file_bytes: bytes) -> tuple[str, list[str]]:
        """Parse a .docx file and extract text with heading-based chapter boundaries.

        Uses python-docx to read paragraph styles. Headings (Heading 1/2/3) become
        chapter markers. Body text is assembled in order.

        Returns (full_text, chapters) where chapters is a list of pre-split chapter
        texts, or an empty list if no heading structure was found (caller should
        fall back to regex splitting).
        """
        from docx import Document
        from io import BytesIO

        doc = Document(BytesIO(file_bytes))
        full_lines = []
        chapter_boundaries = []  # indices into full_lines where chapters start
        current_chapter_lines = []

        FLUSH_EVERY_N_LINES = 200  # prevent chapters from being too large

        def _flush_chapter():
            nonlocal current_chapter_lines
            if current_chapter_lines:
                chapter_boundaries.append(len(full_lines))
                full_lines.extend(current_chapter_lines)
                current_chapter_lines = []

        for para in doc.paragraphs:
            style_name = (para.style.name if para.style else "").lower()
            text = para.text.strip()
            if not text:
                continue

            is_heading = "heading" in style_name or "title" in style_name
            if is_heading:
                _flush_chapter()
                # Mark as chapter header
                current_chapter_lines.append(f"\n{text}\n")
            else:
                current_chapter_lines.append(text)
                if len(current_chapter_lines) >= FLUSH_EVERY_N_LINES:
                    _flush_chapter()

        _flush_chapter()

        full_text = "\n".join(full_lines)

        # Build chapter list from boundaries
        chapters = []
        if len(chapter_boundaries) >= 2:
            for i, start in enumerate(chapter_boundaries):
                end = chapter_boundaries[i + 1] if i + 1 < len(chapter_boundaries) else len(full_lines)
                ch_text = "\n".join(full_lines[start:end]).strip()
                if len(ch_text) > 50:
                    chapters.append(ch_text)

        return full_text, chapters

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs (non-empty lines, stripped)."""
        return [p.strip() for p in text.split('\n') if p.strip()]

    def _score_boundary_candidates(self, paragraphs: list[str]) -> list[tuple[int, float, str]]:
        """Statistical boundary scoring. Returns [(index, score, reason), ...] sorted by score desc.

        No LLM involved. Uses signals:
        - Blank-line gap before paragraph
        - Length anomaly (very short para surrounded by long ones → likely title)
        - Typographic markers (ALL CAPS, separator lines like ---, ***, ===)
        - Vocabulary shift from previous paragraph (word overlap ratio)
        """
        if len(paragraphs) < 4:
            return []

        scores = []
        # Running average paragraph length
        avg_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)

        for i in range(0, len(paragraphs)):
            para = paragraphs[i]
            prev = paragraphs[i - 1] if i > 0 else ""
            score = 0.0
            reasons = []

            # 1. Short paragraph surrounded by long ones → likely title/heading
            para_len = len(para)
            prev_is_long = len(prev) > avg_len * 0.6 if prev else False
            if para_len < avg_len * 0.4 and para_len < 80 and prev_is_long:
                score += 3.0
                reasons.append("short_title")

            # 2. Typographic markers: ALL CAPS, separators
            if re.match(r'^[A-Z\s]{5,}$', para) and len(para) > 5:
                score += 2.0
                reasons.append("all_caps")
            if re.match(r'^[=\-*#]{3,}', para):
                score += 1.5
                reasons.append("separator")

            # 3. Explicit chapter markers (regex — high confidence)
            if re.search(r'第[一二三四五六七八九十百千\d]+[章回节卷集部]', para):
                score += 5.0
                reasons.append("explicit_chapter")
            if re.search(r'Chapter\s*\d+', para, re.IGNORECASE):
                score += 5.0
                reasons.append("chapter_en")
            if re.search(r'^(序章|楔子|终章|尾声|后记|番外|卷[一二三四五六七八九十百千\d]+)', para):
                score += 4.0
                reasons.append("special_section")

            # 4. Time/location shift patterns (regex + keywords)
            shift_pattern = re.search(
                r'(第[一二三四五六七八九十百千\d]+[天日月年]后|'
                r'[一两三四五六七八九十百千\d]+个?[月天年]后|'
                r'与此同时|镜头转[到向]|画面一[转变]|另一方面|'
                r'话分两头|花开两朵|第二天|次日|当晚|午夜|凌晨|清晨|'
                r'不知过了多久|时光飞逝|转眼[间眼]|'
                r'场景切换|地点转换|镜头切换)',
                para[:30]
            )
            if shift_pattern:
                score += 1.5
                reasons.append(f"shift:{shift_pattern.group(0)}")

            # 5. Vocabulary shift from previous paragraph (simple word overlap)
            prev_words = set(re.findall(r'[一-鿿]+', prev))
            curr_words = set(re.findall(r'[一-鿿]+', para))
            if prev_words and curr_words:
                overlap = len(prev_words & curr_words) / len(curr_words | set([""]))
                if overlap < 0.15 and len(para) > 20:
                    score += 1.0
                    reasons.append("vocab_shift")

            # 6. Numbered patterns (1. / 一、 / Part 1)
            if re.match(r'^\d+[\.\、\s]', para) and len(para) < 60:
                score += 1.5
                reasons.append("numbered")

            if score > 0:
                scores.append((i, score, ", ".join(reasons)))

        scores.sort(key=lambda x: -x[1])
        return scores

    async def _llm_confirm_boundaries(self, text: str, candidates: list[tuple[int, float, str]],
                                       paragraphs: list[str]) -> list[str]:
        """One LLM call on sampled context around high-scoring candidates.

        Only sends ~200 chars around each candidate, never the full text.
        Returns list of exact marker strings that start chapters.
        """
        if not candidates:
            return []

        # Take top candidates (max 15 to keep context small)
        top = candidates[:15]

        # Build samples: 200 chars around each candidate paragraph
        samples = []
        for idx, score, reasons in top:
            start = max(0, idx - 2)
            end = min(len(paragraphs), idx + 2)
            snippet = "\n".join(paragraphs[start:end])
            if len(snippet) > 300:
                snippet = snippet[:300]
            samples.append({
                "candidate_idx": idx,
                "score": round(score, 1),
                "reasons": reasons,
                "text": paragraphs[idx][:100],
                "context": snippet,
            })

        prompt = f"""你是一个小说结构分析专家。下面是一本小说的段落样本，我需要你确认哪些位置是真正的章节/分节边界。

对每个候选边界，判断它是否确实开启了一个新章节。返回应该是真正章节开始的准确标记文字（通常是章节标题、数字编号、或第一句话）。

候选边界（按置信度排序）：
{json.dumps(samples, ensure_ascii=False, indent=2)}

请输出纯JSON数组，每个元素是确认的章节起始标记文字（精确字符串，用于分割全文）：
["第一章 标题", "Chapter 2", "***", ...]

规则：
- 只返回确认是真正章节边界的位置
- 标记文字必须与原文完全一致（用于字符串split）
- 不要返回模糊或不确定的边界
- 如果所有候选都不是真正的章节边界，返回空数组 []
- 显式章节标记（第X章、Chapter X）置信度最高"""

        try:
            response = await ai_client.chat([
                {"role": "system", "content": "你是一个小说分析专家。只输出纯JSON数组，不要包含任何其他文字。"},
                {"role": "user", "content": prompt},
            ], temperature=0.1, max_tokens=1000)

            # Extract JSON array from response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                markers = json.loads(json_match.group(0))
                if isinstance(markers, list):
                    logger.info(f"LLM confirmed {len(markers)} chapter boundaries")
                    return markers
        except Exception as e:
            logger.warning(f"LLM boundary confirmation failed: {e}")

        return []

    def _split_chapters(self, text: str, docx_chapters: list[str] | None = None) -> list[str]:
        """Split novel text into chapters using the best available method.

        Priority:
        1. DOCX heading structure (from python-docx parse_docx)
        2. Regex patterns (explicit "第X章", "Chapter N", etc.)
        3. Intelligent detection (statistical scoring → called from adapt_novel async)
        """
        # Use DOCX heading structure if available
        if docx_chapters and len(docx_chapters) >= 3:
            return docx_chapters

        # Regex patterns for explicit chapter markers.
        # Use [^\S\n]* (horizontal whitespace only) to avoid eating newlines.
        patterns = [
            r'\n[^\S\n]*第[一二三四五六七八九十百千\d]+[章回节卷集部][^\S\n]*',
            r'\n[^\S\n]*Chapter\s*\d+[^\S\n]*',
            r'\n[^\S\n]*【第[一二三四五六七八九十百千\d]+[章回节]】[^\S\n]*',
            r'\n[^\S\n]*[=]{3,}[^\S\n]*\n',
            r'\n[^\S\n]*[-]{3,}[^\S\n]*\n',
        ]

        for pattern in patterns:
            splits = re.split(f'({pattern})', text)
            if len(splits) > 3:
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
                chapters = [c for c in chapters if len(c) > 100]
                if len(chapters) >= 3:
                    return chapters

        # Fallback: split by double newlines (noisy but works for scene breaks)
        chunks = re.split(r'\n\s*\n\s*\n', text)
        chunks = [c.strip() for c in chunks if len(c.strip()) > 100]
        if len(chunks) >= 3:
            return chunks

        # Final fallback: equal-length chunks
        chunk_size = max(2000, len(text) // 20)
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    async def _split_chapters_intelligent(self, text: str) -> list[str]:
        """Intelligent chapter detection: statistical pre-filtering + 1 LLM confirmation call.

        Only sends sampled candidate regions to LLM — never dumps full text into context.
        Falls back to _split_chapters result if LLM doesn't improve it.
        """
        paragraphs = self._split_paragraphs(text)
        if len(paragraphs) < 10:
            return self._split_chapters(text)

        # Phase 1: Statistical scoring (no LLM)
        candidates = self._score_boundary_candidates(paragraphs)
        if not candidates:
            return self._split_chapters(text)

        # Phase 2: LLM confirmation (1 call, sampled context only)
        markers = await self._llm_confirm_boundaries(text, candidates, paragraphs)

        # Phase 3: Split using confirmed markers
        if markers and len(markers) >= 2:
            chapters = self._split_by_markers(text, markers)
            chapters = [c.strip() for c in chapters if len(c.strip()) > 100]
            if len(chapters) >= 3:
                logger.info(f"Intelligent split: {len(chapters)} chapters from {len(markers)} LLM-confirmed markers")
                return chapters

        # Fall back to regex-based result
        logger.info("Intelligent split did not improve chapter count, using regex result")
        return self._split_chapters(text)

    def _split_by_markers(self, text: str, markers: list[str]) -> list[str]:
        """Split text using confirmed chapter boundary markers."""
        if not markers:
            return [text]

        # Build regex alternation from markers, sorted longest-first for greedy matching
        escaped = [re.escape(m) for m in sorted(markers, key=len, reverse=True)]
        pattern = '(' + '|'.join(escaped) + ')'

        parts = re.split(pattern, text)
        chapters = []
        current = ""
        for part in parts:
            is_marker = any(part == m for m in markers)
            if is_marker:
                if current.strip():
                    chapters.append(current.strip())
                current = part
            else:
                current += part
        if current.strip():
            chapters.append(current.strip())
        return chapters

    async def _extract_novel_overview(self, text: str, genre: str, style: str) -> dict:
        """Extract novel overview from early chapters."""
        prompt = f"""请从以下小说开头内容中提取关键信息，输出JSON格式。
【重要】请直接输出纯JSON文本，不要用```json代码块包裹。

{text[:6000]}

{{
  "title": "小说标题",
  "main_characters": ["主要角色1", "主要角色2", "主要角色3"],
  "core_conflict": "核心冲突（50字内）",
  "synopsis": "故事梗概（200字内）",
  "setting": "故事背景",
  "time_period": "时代背景",
  "key_relationships": "关键人物关系"
}}"""

        try:
            return await self._call_and_extract_json([
                {"role": "system", "content": "你是一个小说分析专家，擅长提取小说核心信息。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3, max_tokens=1000)
        except Exception as e:
            logger.error(f"Novel overview extraction failed: {e}")
            return {"title": "未命名", "main_characters": [], "core_conflict": "", "synopsis": ""}


script_generator = ScriptGenerator()
