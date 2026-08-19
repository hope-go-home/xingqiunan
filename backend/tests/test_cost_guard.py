"""成本熔断测试：计费估算、预算判断、入口检查（Redis 可用时）"""
import pytest

from app.core import cost_guard


def test_estimate_cost_zero():
    assert cost_guard.estimate_cost(0, 0) == 0.0


def test_estimate_cost_mixed():
    # 100 万输入 token = 0.2 元；100 万输出 = 0.6 元
    assert cost_guard.estimate_cost(1_000_000, 1_000_000) == pytest.approx(0.8)
    assert cost_guard.estimate_cost(500_000, 250_000) == pytest.approx(0.25)


def test_budget_is_exceeded_defaults():
    assert cost_guard.budget_is_exceeded(0.0) is False
    assert cost_guard.budget_is_exceeded(9.9) is False
    assert cost_guard.budget_is_exceeded(10.0) is True


def test_day_key_format():
    import re
    k = cost_guard._day(7, cost_guard.KEY_PREFIX)
    assert re.match(r"^cost:user:7:\d{4}-\d{2}-\d{2}$", k)


@pytest.mark.asyncio
async def test_record_and_check_roundtrip():
    """Redis 记账 + 入口检查闭环（真实 Redis 可用时）"""
    _, used_before = await cost_guard.check_budget(7)
    cost = await cost_guard.record_usage(7, 1_000_000, 0)
    _, used_after = await cost_guard.check_budget(7)
    assert cost == pytest.approx(0.2)
    assert used_after == pytest.approx(used_before + 0.2)