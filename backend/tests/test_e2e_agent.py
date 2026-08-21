# E2E Agent 回归测试：模拟真实用户输入，验证完整 Agent 链路
# 用 Mock LLM 替代真实 API，确保 CI 无需密钥也能跑
# 有真实 API Key 时可跑集成测试（标记 pytest.mark.integration）

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from langchain_core.messages import AIMessage, AIMessageChunk


# ─── Mock LLM：模拟工具调用行为 ───

class MockLLM:
    """模拟 LLM：根据预设脚本返回 tool_call 或文本回答"""

    def __init__(self, script: list[dict]):
        """
        script: [
            {"tool_calls": [{"name": "get_current_time", "args": {}}]},
            {"content": "现在是2026年8月21日"},
        ]
        """
        self._script = script
        self._idx = 0

    def invoke(self, messages):
        return self._call()

    async def ainvoke(self, messages):
        return self._call()

    def _call(self):
        if self._idx >= len(self._script):
            return AIMessage(content="（mock 无预设响应）")
        item = self._script[self._idx]
        self._idx += 1
        if "tool_calls" in item:
            return AIMessage(
                content="",
                tool_calls=item["tool_calls"],
            )
        return AIMessage(content=item.get("content", ""))

    def bind_tools(self, tools, **kwargs):
        """模拟 bind_tools：返回自身（工具绑定由 mock 处理）"""
        return self


# ─── 测试：工具调用链路 ───

class TestToolCallPipeline:
    """验证 Agent 能正确调用工具并返回结果"""

    def test_is_valid_result(self):
        """_is_valid_result 判断逻辑"""
        from app.agents.mcp_agent import McpAgent

        assert McpAgent._is_valid_result("杭州天气：晴天，25°C") is True
        assert McpAgent._is_valid_result("") is False
        assert McpAgent._is_valid_result("无法完成") is False
        assert McpAgent._is_valid_result("失败") is False
        assert McpAgent._is_valid_result("error") is False
        # 有错误关键词但内容够长 → 仍有效（可能在解释错误原因）
        assert McpAgent._is_valid_result("无法直接访问该文件，因为路径不存在，建议检查文件路径是否正确" * 3) is True

    def test_is_valid_result_short_error(self):
        """短错误回答视为无效"""
        from app.agents.mcp_agent import McpAgent

        assert McpAgent._is_valid_result("抱歉，做不到") is False
        assert McpAgent._is_valid_result("出错了") is False


# ─── 测试：Reflection 审查 ───

class TestReflection:
    """验证 Reflection 能检测问题"""

    def test_reflect_sync_no_issues(self):
        """结果一致时返回空"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"issues": [], "re_execute": []}'
            )
            result = agent._reflect_sync("查天气", ["杭州晴天", "上海多云"])
            assert result["issues"] == []
            assert result["re_execute"] == []

    def test_reflect_sync_with_issues(self):
        """结果矛盾时返回问题"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"issues": ["杭州温度数据矛盾"], "re_execute": [0]}'
            )
            result = agent._reflect_sync("查天气", ["杭州30°C", "杭州20°C"])
            assert len(result["issues"]) == 1
            assert 0 in result["re_execute"]

    def test_reflect_sync_single_step_skipped(self):
        """单步任务跳过审查"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        result = agent._reflect_sync("查天气", ["杭州晴天"])
        assert result["issues"] == []

    def test_reflect_sync_parse_error(self):
        """LLM 输出无法解析时优雅降级"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(content="这不是JSON")
            result = agent._reflect_sync("查天气", ["结果1", "结果2"])
            assert result["issues"] == []


# ─── 测试：Failover 逻辑 ───

class TestFailover:
    """验证主模型失败时自动切备用"""

    def test_failover_to_backup(self):
        """主模型抛异常 → 自动切备用模型"""
        from app.agents.mcp_agent import _llm_invoke_with_failover

        call_count = 0
        def mock_invoke(llm, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("主模型挂了")
            return MagicMock(content="备用模型回答")

        with patch("app.agents.mcp_agent._llm_invoke", side_effect=mock_invoke), \
             patch("app.agents.mcp_agent._create_llm", return_value=MagicMock()), \
             patch("app.agents.mcp_agent._create_llm_fallback", return_value=MagicMock()):
            result = _llm_invoke_with_failover("测试 failover")
            assert result.content == "备用模型回答"
            assert call_count == 2

    def test_failover_no_backup_raises(self):
        """主模型失败 + 无备用 → 抛异常"""
        from app.agents.mcp_agent import _llm_invoke_with_failover

        with patch("app.agents.mcp_agent._llm_invoke", side_effect=ConnectionError("主模型挂了")), \
             patch("app.agents.mcp_agent._create_llm", return_value=MagicMock()), \
             patch("app.agents.mcp_agent._create_llm_fallback", return_value=None):
            with pytest.raises(ConnectionError):
                _llm_invoke_with_failover("测试无备用")


# ─── 测试：规划器 ───

class TestPlanner:
    """验证规划器能正确拆解任务"""

    def test_make_plan_sync_simple(self):
        """简单任务返回 None（无需规划）"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(content="SIMPLE")
            result = agent._make_plan_sync("现在几点", ["get_current_time"])
            assert result is None

    def test_make_plan_sync_complex(self):
        """复杂任务返回计划"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='[{"name": "查天气", "action": "查杭州天气"}, {"name": "写总结", "action": "写天气总结"}]'
            )
            result = agent._make_plan_sync("查杭州天气并写总结", ["query_weather", "write_file"])
            assert result is not None
            assert len(result) == 2
            assert result[0]["name"] == "查天气"

    def test_make_plan_sync_json_in_codeblock(self):
        """LLM 用 markdown 代码块包裹 JSON 也能解析"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(
                content='```json\n[{"name": "步骤1", "action": "执行A"}]\n```'
            )
            result = agent._make_plan_sync("执行A", ["run_command"])
            assert result is not None
            assert result[0]["name"] == "步骤1"

    def test_make_plan_sync_invalid_output(self):
        """规划器输出无法解析时降级为 None"""
        from app.agents.mcp_agent import McpAgent

        agent = McpAgent()
        with patch("app.agents.mcp_agent._llm_invoke_with_failover") as mock_llm:
            mock_llm.return_value = MagicMock(content="随便乱写的输出")
            result = agent._make_plan_sync("任务", ["tool_a"])
            assert result is None
