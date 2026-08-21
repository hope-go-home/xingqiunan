# 统一可靠性防护：重试 + 熔断 + 限流
# 用于所有外部 API 调用（dashscope/bocha/amap），防止供应商抖动拖垮系统

import logging
import time
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


# ─── 简易熔断器 ───

class CircuitBreaker:
    """熔断器：连续失败 N 次 → 断开 T 秒 → 半开状态试探一次"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed=正常, open=熔断, half_open=试探

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                return False
            return True
        return False

    def record_success(self):
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning("熔断器打开：连续失败 %d 次，%s 暂时不可用",
                           self._failure_count, getattr(self, "_name", ""))


# ─── 全局熔断器（按供应商隔离）───

_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        _circuit_breakers[name]._name = name
    return _circuit_breakers[name]


# ─── 统一重试装饰器 ───

def resilient_call(provider: str, max_retries: int = 2):
    """为外部 API 调用添加重试 + 熔断防护。

    行为：
        - 偶发失败：自动重试最多 2 次（指数退避：1s → 2s）
        - 连续失败 5 次：熔断 30 秒，期间直接抛异常不再调用
        - 恢复后自动试探一次
    """
    cb = get_circuit_breaker(provider)

    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cb.is_open:
                raise ConnectionError(f"熔断中：{provider} 暂时不可用，请稍后重试")
            try:
                result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception:
                cb.record_failure()
                raise
        return wrapper
    return decorator
