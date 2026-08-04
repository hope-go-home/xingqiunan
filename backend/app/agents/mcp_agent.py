# MCP Agent 引擎：基于 LangChain create_agent（原生 function calling）
# 工作流程：用户输入 → LLM 原生工具选择（tools 协议）→ 执行工具 → LLM 汇总
# 特性：
#   - qwen 原生 function calling（bind_tools），不再依赖 JSON 文本解析
#   - 按 user_id 构建工具（闭包注入），天然用户隔离
#   - 工具失败自动重试（ToolRetryMiddleware）+ 最多 5 轮工具调用（ToolCallLimitMiddleware）
#   - 60 秒总超时，工具结果截断由 tools 层保证
#   - 运行期事件回调（工具调用开始/结束、回答分片），供 WebSocket 推送
# 注意：process() 为同步入口，须在独立线程中调用（如 asyncio.to_thread），内部使用独立事件循环

import asyncio
import time
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

from app.agents.tools import build_tools
from app.core.config import LLM_MODEL, DASHSCOPE_API_KEY

# Agent 系统提示词：说明身份与工具使用原则
SYSTEM_PROMPT = """你是 TaskBench 智能任务助手，可以调用工具完成用户的请求。

工具使用原则：
1. 根据用户需求选择最合适的工具，一次可并行调用多个独立工具
2. 调用工具时给出完整、正确的参数（例如城市名、文件路径、查询内容）
3. 工具返回结果后，基于结果组织最终回答，回答要简洁、准确、直接面向用户
4. 不要虚构工具返回中不存在的信息；工具返回错误时如实说明，并尝试换一种方式重试
5. 如果用户请求不需要任何工具（如闲聊、解释概念），直接回答即可"""

# 最终回答流式分片的字符数（模拟打字效果）
ANSWER_CHUNK_SIZE = 24
# 分片间隔（秒）
ANSWER_CHUNK_INTERVAL = 0.02

# 事件类型（on_event 回调收到的 dict）：
#   {"type": "tool_call",  "name": str, "args": dict}   工具开始调用
#   {"type": "tool_result", "name": str, "result": str} 工具执行完成
#   {"type": "answer",      "content": str}             最终回答分片（含超时/错误兜底文本）


def _emit(on_event: Callable[[dict], None] | None, evt: dict):
    if on_event:
        on_event(evt)


def _to_langchain_messages(history: list[dict]) -> list:
    """把 Redis 上下文（[{"role": ..., "content": ...}]）转成 LangChain 消息"""
    msgs = []
    for item in history or []:
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
        elif role == "system":
            msgs.append(SystemMessage(content=content))
    return msgs


def _stream_answer(on_event, text: str, emit: bool = True):
    """把最终回答切分成片并回调；emit=False 时仅返回文本不推送"""
    if not emit or not on_event or not text:
        return
    text = str(text)
    for i in range(0, len(text), ANSWER_CHUNK_SIZE):
        _emit(on_event, {"type": "answer", "content": text[i:i + ANSWER_CHUNK_SIZE]})
        time.sleep(ANSWER_CHUNK_INTERVAL)


def _create_llm() -> ChatOpenAI:
    """创建 LLM 实例（独立函数便于测试替换）"""
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.1,
    )


class McpAgent:
    """
    Agent 核心类。
    process() 为同步方法：分析需求 → 原生工具调用循环（≤5 轮、失败自动重试）→ 汇总回答。
    须在独立线程调用（asyncio.to_thread），内部通过 asyncio.run 运行完整异步管线。
    """

    def __init__(self, max_steps: int = 5, timeout: float = 60.0):
        self.max_steps = max_steps
        self.timeout = timeout

    def process(
        self,
        user_input: str,
        user_id: int = 0,
        history: list[dict] | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> str:
        """同步入口：返回最终回答文本；on_event 回调会收到工具调用/回答分片事件"""
        try:
            return asyncio.run(self._arun(user_input, user_id, history, on_event))
        except Exception as e:
            reply = f"Agent 执行出错: {e}"
            _emit(on_event, {"type": "answer", "content": reply})
            return reply

    async def _arun(
        self,
        user_input: str,
        user_id: int,
        history: list[dict] | None,
        on_event: Callable[[dict], None] | None,
    ) -> str:
        llm = _create_llm()

        # 原生 function calling + 失败重试（轮数上限用手动计数，不使用中间件）
        agent = create_agent(
            model=llm,
            tools=build_tools(user_id),
            system_prompt=SYSTEM_PROMPT,
            middleware=[ToolRetryMiddleware(max_retries=1, retry_on=Exception)],
        )

        messages = _to_langchain_messages(history)
        messages.append(HumanMessage(content=user_input))

        parts: list[str] = []
        seen_tool_ids: set[str] = set()
        answer_emitted = False
        # 从输入历史之后开始增量处理：历史里的 AI 消息不能被误判为"最终回答"
        msg_index = len(messages)

        def on_tool_call(tc: dict):
            _emit(on_event, {"type": "tool_call", "name": tc.get("name", ""), "args": tc.get("args", {})})

        try:
            async with asyncio.timeout(self.timeout):
                async for event in agent.astream({"messages": messages}, stream_mode="values"):
                    msgs = event.get("messages") or []
                    if not msgs:
                        continue

                    for last in msgs[msg_index:]:
                        # 模型决定调用工具 → 推送 tool_call 事件
                        if isinstance(last, AIMessage):
                            tool_calls = last.tool_calls
                            if tool_calls:
                                for tc in tool_calls:
                                    tid = tc.get("id")
                                    if tid in seen_tool_ids:
                                        continue
                                    seen_tool_ids.add(tid)
                                    on_tool_call(tc)
                                    # 手动轮数限制：一旦超出就推送兜底并返回
                                    if len(seen_tool_ids) > self.max_steps:
                                        limit_text = f"已达到工具调用上限（{self.max_steps} 轮），请简化请求。"
                                        parts.append(limit_text)
                                        _stream_answer(on_event, limit_text)
                                        return "".join(parts)
                            # 无工具调用的 AI 消息 → 最终回答
                            elif last.content and not answer_emitted:
                                answer_emitted = True
                                text = last.content
                                parts.append(text)
                                _stream_answer(on_event, text)
                            continue

                        # 工具执行完成 → 推送 tool_result 事件
                        if getattr(last, "type", "") == "tool":
                            _emit(on_event, {
                                "type": "tool_result",
                                "name": getattr(last, "name", ""),
                                "result": str(getattr(last, "content", ""))[:400],
                            })

                    msg_index = len(msgs)

            # 兜底：未在流中捕捉到回答时，取最后一条 AI 消息
            if not answer_emitted:
                for msg in reversed(msgs):
                    if isinstance(msg, AIMessage) and msg.content:
                        text = msg.content
                        parts.append(text)
                        answer_emitted = True
                        _stream_answer(on_event, text)
                        break

        except TimeoutError:
            text = f"Agent 执行超过 {self.timeout:.0f} 秒，已中断。请简化请求或分步提问。"
            parts.append(text)
            _stream_answer(on_event, text)
        except Exception as e:
            text = f"Agent 执行出错: {e}"
            parts.append(text)
            _stream_answer(on_event, text)

        return "".join(parts) or "（Agent 未能生成回答）"


# 全局单例
agent = McpAgent()
