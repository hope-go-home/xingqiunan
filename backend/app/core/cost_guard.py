# 成本熔断：按用户每日费用预算记账（Redis），入口检查 + 执行中实时熔断
# 计费口径（qwen3.7-plus 标准价，每百万 token）：
#   输入 0.2 元 / 输出 0.6 元 —— 仅用于预算记账，实际账单以厂商为准

import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.core.config import REDIS_URL, COST_DAILY_BUDGET

logger = logging.getLogger(__name__)

KEY_PREFIX = "cost:user:"

_redis = None


class CostLimitExceeded(Exception):
    """执行中累计费用超过当日预算，终止本次 Agent 执行"""


def _get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def _day(user_id: int, prefix: str) -> str:
    """当日 key：{prefix}{user_id}:2026-08-19（UTC 日期，跨天自然归零）"""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}{user_id}:{day}"


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """按 token 用量估算费用（元）"""
    return (input_tokens or 0) / 1_000_000 * 0.2 + (output_tokens or 0) / 1_000_000 * 0.6


def budget_is_exceeded(used_cost: float) -> bool:
    """执行中实时判断：累计费用是否已超当日预算（同步，供回调使用）"""
    return used_cost >= COST_DAILY_BUDGET


async def record_usage(user_id: int, input_tokens: int, output_tokens: int) -> float:
    """把一次请求的用量记入当日累计，返回本次费用（元）"""
    cost = estimate_cost(input_tokens, output_tokens)
    if cost <= 0:
        return 0.0
    try:
        r = _get_redis()
        key = _day(user_id, KEY_PREFIX)
        pipe = r.pipeline()
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, 48 * 3600)  # 48h TTL，防 Redis 长驻垃圾
        await pipe.execute()
    except Exception as e:
        logger.warning("成本记账失败（不影响功能）: %s", e)
    return cost


async def check_budget(user_id: int) -> tuple[bool, float]:
    """入口检查：返回 (可用?, 当日累计费用)"""
    try:
        r = _get_redis()
        used = float(await r.get(_day(user_id, KEY_PREFIX)) or 0.0)
    except Exception as e:
        logger.warning("预算检查失败，放行: %s", e)
        return True, 0.0
    return used < COST_DAILY_BUDGET, round(used, 4)
