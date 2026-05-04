# 剧本工坊 - AI短剧剧本生成平台

AI驱动的短剧/漫剧剧本生成平台，聚合热点趋势，智能生成完整多集剧本。

## 功能特性

- **热点聚合**: 实时抓取红果短剧、番茄小说当前热门内容
- **AI剧本生成**: 基于热点和参考材料，自动生成完整多集短剧剧本
- **分镜脚本**: 每集精确到每个分镜的景别、运镜、画面、台词、AI绘图提示词
- **小说改编**: 上传完整小说，自动改编为短剧剧本
- **知识库管理**: 角色、地点、伏笔等实体持久化，确保长剧本一致性
- **版权风险检测**: 自动检查剧本与已有内容的相似度

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

## 配置

编辑 `backend/.env` 配置AI API密钥:

```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

支持 OpenAI 和 Anthropic 两种AI provider。

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── api/          # API路由
│   │   ├── core/         # 核心配置、数据库、AI客户端
│   │   ├── models/       # 数据模型
│   │   ├── scrapers/     # 红果短剧/番茄小说爬虫
│   │   └── services/     # 业务服务
│   └── run.py            # 启动入口
├── frontend/
│   └── src/
│       ├── pages/        # 页面组件
│       └── services/     # API调用
└── start.sh              # 一键启动脚本
```

## API文档

启动后访问 http://localhost:8000/docs 查看完整API文档。
