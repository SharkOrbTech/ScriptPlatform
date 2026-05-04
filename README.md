# 短剧创作工具

AI驱动的短剧剧本生成平台，聚合热点趋势，智能生成完整多集剧本。

## 功能特性

- **热点聚合**: 实时抓取红果短剧、番茄小说当前热门内容
- **AI剧本生成**: 基于热点和参考材料，自动生成完整多集短剧剧本
- **分镜脚本**: 每集精确到每个分镜的景别、运镜、画面、台词、AI绘图提示词
- **小说改编**: 上传完整小说，自动改编为短剧剧本
- **知识库管理**: 角色、地点、伏笔等实体持久化，确保长剧本一致性
- **版权风险检测**: 自动检查剧本与已有内容的相似度
- **账号系统**: 管理员可创建和管理账号，保障部署安全

## 快速启动

```bash
# 一键启动
./start.sh

# 或手动启动
# 后端
cd backend
source venv/bin/activate
python run.py

# 前端
cd frontend
npm run dev
```

访问 http://localhost:3000

默认管理员账号：`admin` / `admin123`

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
│   │   │   ├── ScriptViewerPage.jsx# 剧本查看页
│   │   │   ├── LoginPage.jsx       # 登录页
│   │   │   └── AccountManagementPage.jsx # 账号管理页
│   │   ├── services/
│   │   │   └── api.js              # API调用封装
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
Phase 1: 故事策划 (Story Planning)
  └─ LLM生成完整故事大纲：角色、场景、道具、世界观、剧情线、伏笔、分集计划

Phase 2: 知识库初始化 (Knowledge Base Init)
  └─ 将角色/场景/道具/规则/伏笔写入知识库

Phase 3: 逐集生成 (Episode Generation)
  └─ 每集：加载上下文 → LLM生成 → 保存 → 更新知识库

Phase 4: 输出整合 (Output Assembly)
  └─ 组装完整剧本对象
```

#### 2. 知识库架构 (`knowledge_base.py`)

```
knowledge_base/{project_id}/
├── manifest.json           # 项目清单
│   ├── entities            # 实体索引
│   ├── plot_threads        # 活跃剧情线
│   ├── foreshadowing       # 未解伏笔
│   └── world_rules         # 世界观规则
├── entities/
│   ├── character_*.json    # 角色实体
│   ├── location_*.json     # 地点实体
│   └── item_*.json         # 道具实体
└── episodes/
    └── episode_*.json      # 每集数据
```

每集生成时自动构建上下文：
- 角色信息（身份、性格、外貌、关系）
- 场景地点
- 关键道具
- 活跃剧情线
- 未解伏笔
- 上一集概要 + 悬念

#### 3. 提示词体系

**STORY_PLANNER_PROMPT** - 故事策划提示词：
- 核心原则（情绪 > 情节）
- 结构框架（10%-80%-10%黄金比例）
- 钩子技法体系（4种开头 + 7种集末）
- 伏笔技法（5种）
- 反转技法（4种）
- 角色塑造（20种反差人设）
- 冲突升级（5层递进）
- 反派套路（7类阴险手段）
- 危机感塑造（3种方法）
- 台词要求（7种高频模式）

**EPISODE_GENERATOR_PROMPT** - 分集生成提示词：
- 单集结构公式
- 压-爽节奏单元
- 台词核心要求
- 钩子类型标记
- Seedance 2.0提示词工程

#### 4. 认证系统

```
登录流程：
  前端 → POST /api/auth/login → 后端验证 → 返回JWT Token
  前端存储Token → 后续请求携带Authorization头

权限模型：
  - 普通用户：访问所有功能
  - 管理员：额外可管理账号（创建/删除）
  - 默认账号：admin / admin123
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
| `/api/auth/login` | POST | 登录 |
| `/api/auth/me` | GET | 获取当前用户 |
| `/api/auth/create-account` | POST | 创建账号（管理员） |
| `/api/auth/accounts` | GET | 账号列表（管理员） |
| `/api/auth/accounts/{username}` | DELETE | 删除账号（管理员） |
| `/api/scripts/generate` | POST | 生成剧本 |
| `/api/scripts/status/{taskId}` | GET | 查询生成状态 |
| `/api/scripts/{scriptId}` | GET | 获取剧本详情 |
| `/api/scripts/list` | GET | 剧本列表 |
| `/api/scripts/qa` | POST | 剧本问答 |
| `/api/scripts/rewrite` | POST | 剧本改写 |
| `/api/scripts/upload-novel` | POST | 小说改编 |
| `/api/trends` | GET | 获取热点 |
| `/api/trends/analysis` | GET | 热点分析 |
| `/api/trends/search` | GET | 搜索热点 |
| `/api/trends/refresh-schedule` | GET/POST | 刷新频率设置 |
| `/api/config` | GET | 获取配置 |
| `/api/health` | GET | 健康检查 |

### 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | LoginPage | 登录页 |
| `/` | TrendsPage | 热点趋势 |
| `/generate` | GeneratorPage | 生成剧本 |
| `/generate/:taskId` | GeneratorPage | 查看生成进度 |
| `/novel` | NovelUploadPage | 小说改编 |
| `/scripts` | ScriptListPage | 我的剧本 |
| `/scripts/:scriptId` | ScriptViewerPage | 剧本详情 |
| `/accounts` | AccountManagementPage | 账号管理（管理员） |

### 技术栈

**后端：**
- FastAPI + Uvicorn
- SQLAlchemy (async) + aiosqlite
- OpenAI / Anthropic API
- ChromaDB (向量数据库)
- JWT认证 + bcrypt密码哈希
- APScheduler (定时任务)

**前端：**
- React 18 + Vite 5
- Tailwind CSS 3
- React Router v6
- Vitest (测试)

### 测试

```bash
# 后端测试
cd backend && python -m pytest tests/

# 前端测试
cd frontend && npx vitest run
```

---

## 写作方法论

本项目内置了基于100+部爆款短剧的完整写作方法论，详见：
- `短剧写作要求.md` - 精炼的写作要求
- `短剧写作技法方法论分析报告.md` - 完整方法论分析
- `剧本分析_*.md` - 各题材深度分析

核心公式：**短剧 = 情绪 > 情节**
