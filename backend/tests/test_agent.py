"""Agent 引擎回归测试：用 FakeLLM 模拟多轮工具调用，覆盖核心链路与兜底场景。

不依赖真实 LLM / MCP 子进程：monkeypatch _create_llm 与 _get_mcp_tools。
"""
import asyncio
import time

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

import app.agents.mcp_agent as mod


class FakeLLM(BaseChatModel):
    """可编程 Fake LLM：按预设响应序列逐轮返回工具调用或最终回答"""

    responses: list = []
    calls: int = 0
    hang: float = 0.0

    def __init__(self, responses, hang: float = 0.0):
        super().__init__()
        self.responses = list(responses)
        self.calls = 0
        self.hang = hang

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.hang:
            time.sleep(self.hang)
            self.hang = 0.0
        return self._next_response()

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        # 异步路径：sleep 可被 asyncio.timeout 取消，超时测试依赖此行为
        if self.hang:
            await asyncio.sleep(self.hang)
            self.hang = 0.0
        return self._next_response()

    def _next_response(self):
        self.calls += 1
        n = min(self.calls - 1, len(self.responses) - 1)
        return ChatResult(generations=[ChatGeneration(message=self.responses[n](None))])

    @property
    def _llm_type(self):
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name, args, cid):
    return lambda m: AIMessage("", [{"name": name, "args": args, "id": cid, "type": "tool_call"}])


def text_resp(content):
    return lambda m: AIMessage(content=content)


def make_agent(monkeypatch, responses, max_steps=5, timeout=60.0, hang=0.0):
    llm = FakeLLM(responses, hang=hang)
    monkeypatch.setattr(mod, "_create_llm", lambda: llm)
    monkeypatch.setattr(mod, "_get_mcp_tools", lambda: [])  # 测试不拉起 MCP 子进程
    monkeypatch.setattr(mod, "PLANNING_ENABLED", False)  # 测试不涉及规划器
    return mod.McpAgent(max_steps=max_steps, timeout=timeout)


def test_normal_tool_chain(monkeypatch):
    """T1: 正常链路 — 两次工具调用 + 最终回答，事件顺序正确"""
    resp = [
        tool_call("list_workspace", {"dir_path": "."}, "c1"),
        tool_call("list_workspace", {"dir_path": "."}, "c2"),
        text_resp("工具执行完毕，回答如下。"),
    ]
    agent = make_agent(monkeypatch, resp)
    events = []
    reply = agent.process("现在几点？看看目录", 7, [{"role": "user", "content": "你好"}], events.append)
    kinds = [e["type"] for e in events]
    assert kinds == ["tool_call", "tool_result", "tool_call", "tool_result", "answer"]
    assert "工具执行完毕" in reply


def test_unknown_tool_does_not_crash(monkeypatch):
    """T2: 模型幻觉出不存在的工具名，Agent 不崩溃"""
    resp = [tool_call("nonexistent_tool", {}, "bad1"), text_resp("兜底回答")]
    agent = make_agent(monkeypatch, resp)
    reply = agent.process("测试", 7)
    assert reply


def test_step_limit(monkeypatch):
    """T3: 轮数上限 — 超过 max_steps 后推送兜底文案并终止"""
    resp = [tool_call("get_current_time", {}, f"c{i}") for i in range(10)] + [text_resp("到上限了")]
    agent = make_agent(monkeypatch, resp, max_steps=2)
    events = []
    reply = agent.process("转圈", 7, on_event=events.append)
    calls = [e for e in events if e["type"] == "tool_call"]
    assert len(calls) == 3  # 触发上限前恰好执行 max_steps+1 次
    assert "上限" in reply


def test_timeout_fallback(monkeypatch):
    """T4: 总超时 — 超过 timeout 秒推送中断文案"""
    agent = make_agent(monkeypatch, [text_resp("慢了")], timeout=2, hang=10.0)
    t0 = time.time()
    reply = agent.process("慢", 7)
    assert "中断" in reply
    assert time.time() - t0 < 10  # 没有真的等到挂起结束


def test_tool_exception_does_not_crash(monkeypatch):
    """T5: 工具抛异常（文件不存在）不崩溃"""
    resp = [tool_call("parse_document", {"file_path": "/nonexistent"}, "e1"), text_resp("文件不存在，已告知用户")]
    agent = make_agent(monkeypatch, resp)
    reply = agent.process("读文件", 7)
    assert reply


def test_process_exception_returns_error_text(monkeypatch):
    """T6: process 顶层异常时返回错误文案而不是抛出"""
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(mod.McpAgent, "_arun", boom)
    events = []
    reply = mod.McpAgent().process("hi", 1, on_event=events.append)
    assert "出错" in reply
    assert any(e["type"] == "answer" for e in events)
