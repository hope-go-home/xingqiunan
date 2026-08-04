# TaskBench — 智能任务自动化工作台

基于 **LangChain Agent + RAG** 的企业级智能工作平台。LLM 自主编排工具链完成任务，WebSocket 流式实时输出，Chroma 向量库驱动知识库语义检索。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    浏览器 (localhost:5173)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ 总览面板  │ │ 任务管理  │ │ AI 对话   │ │   知识库      │   │
│  │ 统计卡片  │ │ 创建+列表 │ │ WS 流式   │ │ 搜索+CRUD     │   │
│  └──────────┘ └──────────┘ └─────┬─────┘ └──────────────┘   │
└──────────────────────────────────┼──────────────────────────┘
                                   │ WebSocket + HTTP REST
                              ┌────┴────┐
                              │  Vite   │ 代理 /api → :8000
                              └────┬────┘
                                   │
┌──────────────────────────────────┼──────────────────────────┐
│                    FastAPI (:8000)                           │
│  ┌──────────┐ ┌──────────┐ ┌────┴─────┐ ┌──────────────┐   │
│  │ 认证模块  │ │ 文件模块  │ │ 聊天模块  │ │  知识库模块   │   │
│  │ JWT+bcrypt│ │ 上传+存储 │ │ LLM+Agent│ │ Chroma 向量  │   │
│  └──────────┘ └──────────┘ └────┬─────┘ └──────────────┘   │
│                                 │                            │
│               ┌─────────────────┴──────────┐                │
│               │       MCP Agent 引擎        │                │
│               │  LLM 自主分析 → 选择工具 → 执行 → 汇总  │   │
│               └────┬─────┬──────┬──────┬───┘                │
│                    │     │      │      │                     │
│               ┌────┴┐ ┌──┴──┐ ┌─┴──┐ ┌─┴──────┐            │
│               │解析 │ │计算 │ │天气 │ │知识库搜│  …6个工具  │
│               │文档 │ │引擎 │ │查询 │ │索/添加 │            │
│               └────┘ └────┘ └────┘ └────────┘            │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐           │
│  │PostgreSQL│  │  Redis   │  │    Celery      │           │
│  │ 任务/用户 │  │ 缓存/队列 │  │  异步任务执行   │           │
│  └──────────┘  └──────────┘  └────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心功能

### 1. AI Agent 多工具协作

Agent 模式下，LLM 不直接回答，而是**自主分析需求 → 选择工具 → 执行 → 汇总结果**。

| 工具名 | 功能 | 示例 |
|--------|------|------|
| `parse_document` | 解析 TXT/MD/JSON 文件 | "帮我读一下这个文件内容" |
| `list_directory` | 浏览目录结构 | "upload 目录下有什么文件" |
| `calculate` | 数学四则运算 | "总价 (100+200)*3 是多少" |
| `query_weather` | 高德实时天气 | "查一下杭州明天下不下雨" |
| `search_knowledge` | 知识库语义搜索 | "知识库里有没有关于报销的文档" |
| `add_knowledge` | 添加文档到知识库 | "把这段文字存到知识库" |

Agent 最多迭代 5 轮，可组合多个工具完成复杂任务。

### 2. WebSocket 流式对话

普通模式下 LLM 逐字流式输出，首字延迟 <200ms，体验类似 ChatGPT 打字效果。

### 3. RAG 知识库

- 基于 Chroma 向量数据库，本地持久化
- 用户间数据隔离（每人独立 Collection）
- 支持语义搜索（不依赖关键词匹配）

### 4. 异步任务执行

创建任务后自动提交 Celery 队列异步执行，任务状态实时更新（pending → running → completed/failed）。

---

## 快速启动

### 前置条件

- Python 3.10+
- Node.js 18+
- PostgreSQL + Redis（推荐 Docker）

### 1. 启动基础设施

```bash
cd deploy
docker compose -f docker-compose.yml up -d
```

### 2. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 3. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env，填入 API Key：
#   DASHSCOPE_API_KEY=sk-xxx    # 通义千问
#   AMAP_API_KEY=xxx            # 高德地图（天气查询）
```

### 4. 启动服务

```bash
# 终端 1：后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2：Celery Worker（异步任务）
cd backend
celery -A app.tasks.celery_app worker --pool=solo -l info

# 终端 3：前端
cd frontend
npm run dev
```

打开 http://localhost:5173

---

## 项目结构

```
TaskBench/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── core/
│   │   │   ├── config.py              # 配置（load_dotenv + os.getenv）
│   │   │   ├── database.py            # 异步 SQLAlchemy 引擎
│   │   │   ├── security.py            # JWT + bcrypt
│   │   │   └── websocket_manager.py   # WebSocket 连接池
│   │   ├── models/                    # ORM 模型（User/FileRecord/Task）
│   │   ├── schemas/                   # Pydantic 请求/响应体
│   │   ├── api/                       # 路由（auth/files/tasks/chat/knowledge）
│   │   ├── services/                  # 业务逻辑层
│   │   ├── agents/
│   │   │   ├── tools.py               # 6 个工具函数 + 注册表
│   │   │   └── mcp_agent.py           # Agent 引擎（LLM 决策 + 工具执行）
│   │   └── tasks/
│   │       ├── celery_app.py          # Celery 配置
│   │       └── file_tasks.py          # 异步任务定义
│   ├── .env
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.js                    # Vue 入口
│   │   ├── App.vue                    # 全局壳（侧边栏 + KeepAlive）
│   │   ├── router/index.js            # 路由 + 登录守卫
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── api/                       # Axios + WebSocket 客户端
│   │   ├── views/                     # 5 个页面
│   │   └── components/                # 3 个可复用组件
│   └── vite.config.js
│
├── deploy/
│   └── docker-compose.yml             # PostgreSQL + Redis 部署
└── README.md
```

---

## API 速查

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 注册 | — |
| POST | `/auth/login` | 登录 → JWT | — |
| POST | `/files/upload` | 上传文件 | Bearer |
| POST | `/tasks/` | 创建任务 → 触发 Celery | Bearer |
| GET | `/tasks/` | 任务列表 | Bearer |
| GET | `/tasks/{id}` | 任务详情 | Bearer |
| WS | `/chat/ws` | 流式对话 / Agent | — |
| POST | `/knowledge/add` | 添加文档 | Bearer |
| GET | `/knowledge/search` | 语义搜索 | Bearer |
| GET | `/knowledge/list` | 文档列表 | Bearer |
| DELETE | `/knowledge/{id}` | 删除文档 | Bearer |

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| AI 引擎 | LangChain + ChatOpenAI (qwen3.7-plus) |
| Agent | 自研工具注册 + LLM 决策循环 |
| 向量库 | Chroma（本地持久化） |
| 数据库 | PostgreSQL（async SQLAlchemy） |
| 缓存/队列 | Redis |
| 异步任务 | Celery |
| 前端框架 | Vue 3 (Composition API) |
| 状态管理 | Pinia |
| 实时通信 | WebSocket (流式输出) |
| 构建 | Vite |
| 部署 | Docker Compose |

---

## Agent 工作流程

```
用户: "帮我查一下杭州的天气，然后看看知识库里有没有关于杭州的旅游攻略"

    ┌───────▼────────┐
    │  LLM 分析需求   │ → "需要两个工具: query_weather + search_knowledge"
    └───────┬────────┘
            │
   ┌────────▼─────────┐
   │ 第1轮: query_weather("杭州")
   │ → 返回: 📍 杭州 晴 25°C~34°C
   └────────┬─────────┘
            │
   ┌────────▼─────────┐
   │ 第2轮: search_knowledge("杭州旅游攻略")
   │ → 返回: 找到2条相关内容…
   └────────┬─────────┘
            │
   ┌────────▼─────────┐
   │ LLM 汇总结果      │ → "杭州今天晴天 25~34°C，适合出行。
   │ 返回最终回答      │    知识库中有2条杭州旅游相关文档…"
   └──────────────────┘
```
