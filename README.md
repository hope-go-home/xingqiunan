# TaskBench — 智能任务自动化工作台

基于 **LangChain Agent + MCP 协议 + RAG** 的智能工作平台。LLM 自主编排工具链完成任务，
WebSocket 流式实时输出，Chroma 向量库驱动知识库语义检索。

## 核心亮点

### 1. Agent 工具编排引擎
LLM 原生 function calling 驱动：分析需求 → 选择工具 → 执行 → 汇总。工具分两层接入：

| 层 | 方式 | 工具 |
|----|------|------|
| **MCP 协议层**（外部服务） | 本地 MCP Server（`app/agents/mcp_server.py`），Agent 经 `langchain-mcp-adapters` 连接 | `get_current_time`、`query_weather` |
| **本地注册层**（用户态） | 闭包注入 `user_id`，天然多租户隔离 | `parse_document`、`list_directory`、`list_tasks`、`translate`、`create_task`、`search_knowledge`、`add_knowledge`、`analyze_image`、`ocr_image`、`web_search`、`write_file`、`read_file`、`list_workspace`、`create_directory`、`delete_file`、`move_file`、`run_command`、`read_project_file`、`install_skill`、`list_skills`、`load_skill` |

- 最多 5 轮工具调用，60s 总超时，工具失败自动重试（ToolRetryMiddleware）
- 工具结果统一截断（2000 字符），防止撑爆 LLM 上下文
- 事件驱动回传：`tool_call` / `tool_result` / `answer` / `usage` 四种事件实时推送前端

### 2. WebSocket 流式对话 + 过程可视化
- 握手时校验 JWT（`?token=`），user_id 一律从 token 解析，不信任客户端上报
- Origin 白名单校验（防 CSWSH）
- 普通模式逐字流式；Agent 模式工具调用过程实时展示，回答分片推送
- 会话级上下文隔离（Redis key 含 session_id）+ 超长自动 LLM 摘要压缩

### 3. 安全与成本
- **Prompt 注入防御**：文件内容以数据标记包裹并声明"指令无效"，Agent 系统提示词含安全边界规则
- **多租户文件沙箱**：`uploads/user_{id}/` 隔离，工具路径校验防穿越
- **上传限制**：类型白名单 + 20MB 上限 + 分块流式写入
- **成本核算**：每次调用 token 用量落库 `token_usage` 表，支撑成本统计

### 4. RAG 知识库
Chroma 向量检索，按用户 Collection 隔离，支持语义搜索。文档管理见另一个 RAG 专项项目。

### 5. 异步任务
创建任务后提交 Celery 队列异步执行，状态实时流转（pending → running → completed/failed）。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLAlchemy(async) + PostgreSQL |
| AI | LangChain + ChatOpenAI（通义千问） |
| 工具接入 | MCP 协议（`mcp` SDK + `langchain-mcp-adapters`） |
| 队列/缓存 | Celery + Redis |
| 向量库 | Chroma（本地持久化） |
| 前端 | Vue 3 + Pinia + Vite + WebSocket |

## 快速启动

前置条件：Python 3.10+、Node.js 18+、PostgreSQL + Redis（推荐 Docker）。

```bash
# 1. 基础设施
cd deploy && docker compose up -d

# 2. 后端
cd backend
pip install -r requirements.txt
cp ../.env.example .env        # 填入 DASHSCOPE_API_KEY / AMAP_API_KEY / SECRET_KEY
python -m uvicorn app.main:app --port 8000

# 3. Celery Worker（异步任务）
celery -A app.tasks.celery_app worker --pool=solo -l info

# 4. 前端
cd frontend && npm install && npm run dev
```

打开 http://localhost:5173

## 测试

```bash
cd backend && python -m pytest
```

23 个用例覆盖：Agent 引擎（FakeLLM 模拟多轮工具调用、超时、轮数上限、异常工具）、
JWT 安全、文件沙箱防穿越、Schema 校验。`tests/test_agent.py` 中的 FakeLLM
不依赖真实模型，可在无 API Key 环境运行。

## 项目结构

```
backend/
├── app/
│   ├── main.py                # FastAPI 入口（CORS 白名单、日志、建表）
│   ├── core/                  # 配置 / 数据库 / JWT / WS 连接管理
│   ├── api/                   # auth / files / tasks / chat / knowledge
│   ├── agents/
│   │   ├── tools.py           # 本地工具注册表（闭包注入 user_id）
│   │   ├── mcp_server.py      # MCP Server：外部服务工具（天气/时间）
│   │   └── mcp_agent.py       # Agent 引擎（LLM 决策 + 工具执行 + 事件回传）
│   ├── services/              # 业务逻辑层
│   ├── models/                # ORM（含 token_usage 成本统计表）
│   ├── tasks/                 # Celery 配置与异步任务
│   └── tests/                 # pytest 测试套件
├── mcp_servers.json           # MCP 客户端连接配置
└── requirements.txt

frontend/
└── src/
    ├── api/chat.js            # WebSocket 客户端（token 认证 + 断线重连）
    ├── components/ChatPanel.vue  # 聊天面板（Agent 工具日志独立展示）
    ├── views/                 # 总览 / 对话 / 知识库 / 登录
    └── stores/                # Pinia（user / task）
```

## 技术选型与取舍（面试向）

- **为什么工具分两层？** 外部服务（天气/时间）与用户态工具（文件/知识库）职责不同：
  前者无状态、与用户无关，适合走 MCP 协议标准化接入；后者必须绑定 `user_id`
  做数据隔离，闭包注入比参数传递更不易被 LLM 篡改。
- **为什么 MCP 用 stdio 而不是 HTTP？** 单机演示场景 stdio 零配置、免端口；
  多机部署可平滑替换为 streamable HTTP 传输，连接配置在 `mcp_servers.json` 一处维护。
- **为什么 WebSocket 而不是 SSE？** 需要承载双向事件（工具调用过程推送 + 停止指令），
  SSE 只能单向。
- **JWT 放哪里？** 当前放 localStorage（开发便捷）。已知风险：XSS 可窃取 token；
  生产化应换 httpOnly cookie + CSRF 防护，或短效 access + refresh token。
- **上下文压缩策略**：超过 30 条消息对早期内容做 LLM 摘要（结果缓存 6 小时），
  保留最近 10 条原文，控制 token 成本同时不丢失关键事实。
- **已知局限**：WS 连接池为单进程内存实现，多实例部署需 Redis pub/sub 或粘性会话；
  Chroma 为嵌入式模式，多进程下需换 server 模式或 pgvector。
