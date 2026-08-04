import os, sys, time
os.environ["DASHSCOPE_API_KEY"] = "sk-test"
sys.path.insert(0, r"D:\项目\智能任务自动化工作台\backend")

import app.agents.mcp_agent as mod
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_FAKE_RESPONSES: list = []
_FAKE_CALLS: list = [0]
_FAKE_HANG: list = [0.0]

class FakeLLM(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if _FAKE_HANG[0]:
            time.sleep(_FAKE_HANG[0])
            _FAKE_HANG[0] = 0.0
        _FAKE_CALLS[0] += 1
        n = min(_FAKE_CALLS[0] - 1, len(_FAKE_RESPONSES) - 1)
        return ChatResult(generations=[ChatGeneration(message=_FAKE_RESPONSES[n](messages))])
    @property
    def _llm_type(self): return "fake"
    def bind_tools(self, tools, **kwargs): return self

def tool_call(name, args, cid):
    return lambda m: AIMessage("", [{"name": name, "args": args, "id": cid, "type": "tool_call"}])
def text_resp(content):
    return lambda m: AIMessage(content=content)

mod.ChatOpenAI = FakeLLM
mod._create_llm = lambda: FakeLLM()

# ── T1: 正常链路 ──
_FAKE_RESPONSES[:] = [tool_call("get_current_time", {}, "c1"), tool_call("list_directory", {"dir_path": "."}, "c2"), text_resp("现在是北京时间，uploads 目录内容已列出。")]
_FAKE_CALLS[0] = 0
events = []
reply = mod.McpAgent(max_steps=5).process("现在几点了？顺便看看 uploads 里有什么", 7, [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}], events.append)
kinds = [e["type"] for e in events]
assert kinds == ["tool_call", "tool_result", "tool_call", "tool_result", "answer"], f"T1 kinds: {kinds}"
assert "uploads" in reply, f"T1 reply: {reply}"
print("T1 PASS")

# ── T2: 不存在的工具名不崩溃 ──
_FAKE_RESPONSES[:] = [tool_call("nonexistent_tool", {}, "bad1"), text_resp("兜底回答")]
_FAKE_CALLS[0] = 0
reply2 = mod.McpAgent(max_steps=5).process("测试", 7)
assert reply2, "T2 不应崩溃"
print("T2 PASS")

# ── T3: 轮数上限 ──
_FAKE_RESPONSES[:] = [tool_call("get_current_time", {}, f"c{i}") for i in range(10)] + [text_resp("到上限了")]
_FAKE_CALLS[0] = 0
events3 = []
reply3 = mod.McpAgent(max_steps=2).process("转圈", 7, on_event=events3.append)
calls3 = [e for e in events3 if e["type"] == "tool_call"]
assert len(calls3) == 3, f"T3 应恰好 3 次(>max_steps=2 触发上限): {len(calls3)}"
assert "上限" in reply3, f"T3 reply: {reply3}"
print(f"T3 PASS (calls={len(calls3)})")

# ── T4: 超时兜底 ──
_FAKE_RESPONSES[:] = [text_resp("慢了")]
_FAKE_HANG[0] = 10.0
_FAKE_CALLS[0] = 0
t0 = time.time()
reply4 = mod.McpAgent(max_steps=5, timeout=2).process("慢", 7)
assert "中断" in reply4, f"T4 reply: {reply4}"
print(f"T4 PASS ({time.time()-t0:.1f}s)")

# ── T5: 工具抛异常不崩溃 ──
_FAKE_RESPONSES[:] = [tool_call("parse_document", {"file_path": "/nonexistent"}, "e1"), text_resp("文件不存在，已告知用户")]
_FAKE_CALLS[0] = 0
reply5 = mod.McpAgent(max_steps=5).process("读文件", 7)
assert reply5, "T5 不应崩溃"
print("T5 PASS")

print("\nALL 5 TESTS PASSED")
