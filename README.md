# 短剧创作工具

AI驱动的短剧剧本生成平台，聚合热点趋势，智能生成完整多集剧本。

## 功能特性

- **热点聚合**: 实时抓取红果短剧、番茄小说当前热门内容
- **AI剧本生成**: 基于热点和参考材料，自动生成完整多集短剧剧本（最多200集）
- **分镜脚本**: 每集精确到每个分镜的景别、运镜、画面、台词、内心独白、视频生成提示词
- **视频生成提示词**: 每个镜头输出完整的AI视频模型指令（全中文自然语言，角色用【角色名】引用，包含台词/独白/动作/光影/音效），用户可一键复制给视频生成模型
- **旁白系统**: 旁白仅限内心独白（OS），台词与旁白在同一镜头互斥，字数灵活不强制
- **钩子标记系统**: 自然融入剧情，仅在关键节点标记钩子类型（hook/cliffhanger/foreshadowing/turning_point/emotional_peak/revelation/conflict），前端彩色高亮显示
- **小说智能改编**: 支持数百万字超长小说，分层摘要 + 关键章节提取，不塞入全量上下文
- **原著钩子提取**: 改编小说时自动提取原著中的悬念点、反转、情感高潮，确保改编忠实原著节奏
- **知识库管理**: 角色、地点、伏笔等实体持久化，确保长剧本一致性
- **版权风险检测**: 自动检查剧本与已有内容的相似度
- **多格式导出**: 支持 Markdown、DOCX 单文件导出，以及 ZIP 打包分文件导出（概述/角色/剧本/场景/道具）
- **账号系统**: 管理员可创建和管理账号，保障部署安全

## 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

## 快速启动

```bash
# 一键启动
./start.sh

# 或手动启动
# 后端
cd backend
python run.py

# 前端
cd frontend
npm run dev
```

访问 http://localhost:3000

## 配置

编辑 `backend/.env` 配置AI API密钥:

```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

支持 OpenAI 和 Anthropic 两种AI provider。

---

## 项目架构

### 目录结构

```
script/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── api/                    # API路由层
│   │   │   ├── auth.py             # 认证接口：登录、创建账号、账号管理
│   │   │   ├── scripts.py          # 剧本接口：生成、状态查询、列表、QA、改写
│   │   │   └── trends.py           # 热点接口：趋势数据、分析、搜索
│   │   ├── core/                   # 核心模块
│   │   │   ├── ai_client.py        # 统一AI客户端（OpenAI/Anthropic）
│   │   │   ├── auth.py             # JWT认证、密码哈希、Token管理
│   │   │   ├── config.py           # 配置管理（Pydantic Settings）
│   │   │   └── database.py         # SQLAlchemy异步数据库（SQLite）
│   │   ├── models/                 # 数据模型
│   │   │   └── schemas.py          # Pydantic Schema定义
│   │   ├── scrapers/               # 数据爬虫
│   │   │   ├── base.py             # 爬虫基类
│   │   │   ├── hongguo.py          # 红果短剧爬虫
│   │   │   └── tomato.py           # 番茄小说爬虫
│   │   └── services/               # 业务服务层
│   │       ├── script_generator.py # 剧本生成引擎（核心）
│   │       ├── knowledge_base.py   # 知识库管理
│   │       ├── trend_service.py    # 热点趋势服务
│   │       └── copyright_checker.py# 版权风险检测
│   ├── tests/                      # 测试
│   ├── requirements.txt            # Python依赖
│   └── run.py                      # 启动入口
│
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── pages/                  # 页面组件
│   │   │   ├── TrendsPage.jsx      # 热点趋势页
│   │   │   ├── GeneratorPage.jsx   # 剧本生成页
│   │   │   ├── NovelUploadPage.jsx # 小说改编页
│   │   │   ├── ScriptListPage.jsx  # 剧本列表页
│   │   │   ├── ScriptViewerPage.jsx# 剧本查看页（含钩子高亮）
│   │   │   ├── LoginPage.jsx       # 登录页
│   │   │   └── AccountManagementPage.jsx # 账号管理页
│   │   ├── services/
│   │   │   ├── api.js              # API调用封装
│   │   │   └── exportUtils.js      # 导出工具（Markdown/DOCX/ZIP）
│   │   ├── App.jsx                 # 主应用组件、路由、认证
│   │   ├── main.jsx                # 入口
│   │   └── index.css               # 全局样式
│   ├── index.html
│   └── package.json
│
├── reference_new/                  # 参考剧本（gitignore）
│   ├── 方法论/                     # 写作方法论文档
│   ├── 短剧写作教程/               # 教程文档
│   └── *.docx                      # 100+部完整剧本
│
├── 短剧写作要求.md                  # 精炼的写作要求
├── 短剧写作技法方法论分析报告.md     # 完整方法论分析
├── 剧本分析_*.md                   # 各题材剧本分析报告
├── start.sh                        # 一键启动脚本
└── .gitignore
```

### 核心架构

#### 1. 剧本生成引擎 (`script_generator.py`)

生成流程分为4个阶段：

```
Phase 1: 故事策划
  └─ LLM生成完整故事大纲：角色、场景、道具、世界观、剧情线、伏笔、分集计划、核心悬念

Phase 2: 知识库初始化
  └─ 将角色/场景/道具/规则/伏笔写入知识库文件系统

Phase 3: 逐集生成
  └─ 每集：加载知识库上下文 → LLM生成分镜脚本 → 保存 → 提取新实体更新知识库

Phase 4: 输出整合
  └─ 组装完整剧本对象（角色 + 场景 + 道具 + 每集分镜）
```

#### 2. 知识库架构 (`knowledge_base.py`)

```
knowledge_base/{project_id}/
├── manifest.json           # 项目清单
│   ├── entities            # 实体索引（名称→文件映射）
│   ├── plot_threads        # 活跃剧情线
│   ├── foreshadowing       # 未解伏笔（伏笔描述、埋设集数、揭晓集数）
│   └── world_rules         # 世界观规则
├── entities/
│   ├── character_*.json    # 角色实体（身份、性格、外貌、关系、成长弧线）
│   ├── location_*.json     # 地点实体（场景描述、氛围、时间）
│   └── item_*.json         # 道具实体（描述、首次出现集数）
└── episodes/
    └── episode_*.json      # 每集数据（标题、概要、分镜、钩子）
```

每集生成时自动构建上下文：
- 角色信息（身份、性格、外貌、关系、成长弧线）
- 场景地点（氛围、时间、天气）
- 关键道具（象征意义、出现时机）
- 活跃剧情线（状态追踪）
- 未解伏笔（埋设→揭晓对应）
- 世界观规则
- 上一集概要 + 悬念

#### 3. 超长小说智能改编

对超过5万字或20章的小说，采用分层处理策略，避免将全量文本塞入上下文：

```
输入小说（最高支持1000万字）
  │
  ├─ 分批摘要：每5章一批，每章截取3000字 → LLM生成摘要 + 提取钩子
  │   └─ 返回：chapter_summaries[] + chapter_hooks[]
  │
  ├─ 关键章节提取：首尾各2章 + 25%/50%/75%高潮点 + 集边界章 → 全文保留（每章2000字，总计≤15000字）
  │
  └─ 故事策划：摘要索引 + 关键章节全文 + 原著钩子索引 → LLM生成完整策划
      └─ 逐集生成：仅注入该集范围内的章节摘要和钩子
```

#### 4. 原著钩子提取

在分批摘要过程中同时提取每章的钩子（0-3个/章），7种类型：

| hook_type | 含义 | 位置 |
|-----------|------|------|
| `hook` | 开头钩子/爆点 | start |
| `cliffhanger` | 结尾悬念 | end |
| `foreshadowing` | 伏笔 | middle |
| `turning_point` | 情节转折 | any |
| `emotional_peak` | 情感高潮 | any |
| `revelation` | 真相揭露 | any |
| `conflict` | 核心冲突 | any |

钩子注入两个位置：
1. **故事策划阶段**：原著钩子索引作为上下文，确保策划保留原著节奏
2. **逐集生成阶段**：根据章节-集映射，注入该集对应的原著钩子

#### 5. 提示词体系

**video_prompt（视频生成提示词）** — 每个镜头输出，替代旧的ai_prompt/lighting/emotion/sound_effects：
- 全中文自然语言段落，AI指令风格（非文学描写）
- 角色统一使用【角色名】格式引用
- 包含该镜头的完整内容：画面描述 + 角色台词原文 + 内心独白原文 + 说话语气 + 光影氛围 + 音效环境声
- 音频画面一起生成，用户可直接复制粘贴给视频模型

**STORY_PLANNER_PROMPT** — 故事策划提示词（Phase 1 使用）：
- 核心原则：情绪 > 情节
- 结构框架：10%-80%-10%黄金比例
- 钩子技法体系：4种开头 + 7种集末
- 伏笔技法：信物/身份/闪回/对话/道具
- 反转技法：身份/关系/局势/认知
- 角色塑造：20种反差人设模板
- 冲突升级：5层递进（言语→肢体→关系→经济→生命）
- 反派套路：7类阴险手段
- 危机感塑造：信息差/时间锁/生死局
- 台词要求：7种高频模式（侮辱施压/反转/身份揭露/情感拉扯/霸总护短/女主反击/反派嘲讽）
- 八种剧情写法 + 六大矛盾来源 + 30个爽感来源

**EPISODE_GENERATOR_PROMPT** — 分集生成提示词（Phase 3 使用）：
- 与策划提示词共享完整方法论体系（反差人设、反派套路、伏笔技法、反转技法等）
- 单集结构公式：10%-80%-10%黄金比例
- 压-爽节奏：至少1个循环，允许跨集，不强制每集都存在
- 台词核心要求：400-700字/集（动态计算：时长秒数 × 5~8字）
- 旁白仅限内心独白（OS），字数灵活，台词与旁白同一镜头互斥
- 钩子类型标记：谨慎使用，一集通常2-4个标记，绝大多数镜头用null
- 景别/运镜/转场规范
- 视频生成提示词要求（AI指令风格，全中文）

#### 6. 钩子标记系统

仅在关键分镜节点标注 `hook_type`（一集通常2-4个，其余为null），支持7种钩子类型：

| hook_type | 含义 | 前端颜色 |
|-----------|------|----------|
| `hook` | 开头钩子/爆点 | 红色背景 |
| `cliffhanger` | 结尾悬念 | 琥珀色背景 |
| `foreshadowing` | 伏笔 | 紫色背景 |
| `turning_point` | 情节转折 | 蓝色背景 |
| `emotional_peak` | 情感高潮 | 粉色背景 |
| `revelation` | 真相揭露 | 绿色背景 |
| `conflict` | 核心冲突 | 橙色背景 |

前端 `ScriptViewerPage` 的 `ShotCard` 组件根据 `hook_type` 渲染彩色左边框和背景标签。

#### 7. 认证系统

```
登录流程：
  前端 → POST /api/auth/login → 后端验证密码 → 返回JWT Token
  前端存储Token到localStorage → 后续请求携带Authorization: Bearer头
  401响应 → 自动跳转登录页

权限模型：
  - 普通用户：访问所有功能
  - 管理员：额外可管理账号（创建/删除）
```

### 数据库模型

```python
# 用户表
UserDB: id, username, password_hash, is_admin, created_at

# 剧本表
ScriptDB: id, title, genre, logline, synopsis, characters, episodes,
          theme, emotional_tone, status, progress, created_at

# 热点表
TrendDB: id, title, source, category, heat, description, tags, scraped_at

# 任务表
TaskDB: id, task_type, status, progress, result, error, created_at
```

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 登录，返回JWT Token |
| `/api/auth/me` | GET | 获取当前用户信息 |
| `/api/auth/create-account` | POST | 创建账号（管理员） |
| `/api/auth/accounts` | GET | 账号列表（管理员） |
| `/api/auth/accounts/{username}` | DELETE | 删除账号（管理员） |
| `/api/auth/change-password` | POST | 修改密码 |
| `/api/scripts/generate` | POST | 生成剧本（返回taskId） |
| `/api/scripts/status/{taskId}` | GET | 查询生成状态/结果 |
| `/api/scripts/{scriptId}` | GET | 获取剧本详情 |
| `/api/scripts/list` | GET | 剧本列表 |
| `/api/scripts/qa` | POST | 剧本问答 |
| `/api/scripts/rewrite` | POST | 剧本改写 |
| `/api/scripts/upload-novel` | POST | 小说改编 |
| `/api/trends` | GET | 获取热点列表 |
| `/api/trends/analysis` | GET | 热点分析统计 |
| `/api/trends/search` | GET | 搜索热点 |
| `/api/trends/refresh-schedule` | GET/POST | 刷新频率设置 |
| `/api/config` | GET | 获取配置（题材列表等） |
| `/api/health` | GET | 健康检查 |

### 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | LoginPage | 登录页 |
| `/` | TrendsPage | 热点趋势 |
| `/generate` | GeneratorPage | 生成剧本（步骤式表单） |
| `/generate/:taskId` | GeneratorPage | 查看生成进度 |
| `/novel` | NovelUploadPage | 小说改编 |
| `/scripts` | ScriptListPage | 我的剧本列表 |
| `/scripts/:scriptId` | ScriptViewerPage | 剧本详情（分镜+钩子高亮） |
| `/accounts` | AccountManagementPage | 账号管理（管理员） |

### 技术栈

**后端：**
- FastAPI + Uvicorn（异步Web框架）
- SQLAlchemy (async) + aiosqlite（异步ORM + SQLite）
- OpenAI / Anthropic API（双AI provider支持）
- JWT认证 + bcrypt密码哈希
- APScheduler（定时热点刷新）

**前端：**
- React 18 + Vite 5
- Tailwind CSS 3（实用优先样式）
- React Router v6（客户端路由）
- docx（DOCX文件生成）
- JSZip + file-saver（ZIP打包导出）
- Vitest + Testing Library（测试）

### 测试

```bash
# 快速E2E测试（Mocked LLM，~2秒，40个测试覆盖全部API）
cd backend && python /tmp/e2e_fast_test.py

# 后端API测试
cd backend && python -m pytest tests/test_api.py

# 后端生成引擎测试（含真实AI调用，较慢）
cd backend && python -m pytest tests/test_script_generator.py

# 前端测试
cd frontend && npx vitest run
```

快速E2E测试使用 httpx AsyncClient + ASGITransport 直接测试 FastAPI 应用，无需启动真实服务器，Mock 所有LLM调用，覆盖：登录认证、权限管理、剧本生成全流程（含video_prompt字段验证）、状态轮询、剧本详情、列表查询、QA问答、小说上传、密码修改、200集上限验证等。

---

## 写作方法论

本项目内置了基于100+部爆款短剧的完整写作方法论，详见：
- `短剧写作要求.md` - 精炼的写作要求
- `短剧写作技法方法论分析报告.md` - 完整方法论分析
- `剧本分析_*.md` - 各题材深度分析（重生复仇、甜宠逆袭、悬疑灵异、古装穿越）
- `方法论分析_教程.md` - 教程文档分析

核心公式：**短剧 = 情绪 > 情节**

三条铁律：不要铺垫（矛盾前置）、不要想当然（写市场需要的）、用不到天赋（靠套路公式）。
