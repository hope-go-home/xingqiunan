# Prometheus 可观测性指标：请求计数、LLM 耗时、工具成功率、费用累计

from prometheus_client import Counter, Histogram, Gauge

# ─── HTTP 请求 ───

http_requests_total = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时（秒）",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ─── LLM 调用 ───

llm_calls_total = Counter(
    "llm_calls_total",
    "LLM 调用总数",
    ["model", "status"],  # status: success / error / failover
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM 调用耗时（秒）",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM token 用量",
    ["model", "direction"],  # direction: input / output
)

# ─── 工具调用 ───

tool_calls_total = Counter(
    "tool_calls_total",
    "工具调用总数",
    ["tool_name", "status"],  # status: success / error
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "工具调用耗时（秒）",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# ─── 费用 ───

cost_yuan_total = Counter(
    "cost_yuan_total",
    "累计费用（元）",
    ["user_id"],
)

# ─── Agent 会话 ───

agent_sessions_total = Counter(
    "agent_sessions_total",
    "Agent 会话总数",
    ["status"],  # status: completed / error / timeout / cancelled
)

agent_session_duration_seconds = Histogram(
    "agent_session_duration_seconds",
    "Agent 会话耗时（秒）",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# ─── 系统 ───

active_websocket_connections = Gauge(
    "active_websocket_connections",
    "当前活跃 WebSocket 连接数",
)
