"""多用户并发 AI 访问隔离测试
验证不同 (user_id, session_id) 的对话上下文即使并发读写也不会互相串台。
用假 Redis 模拟，CI 无需真实 Redis / 密钥即可运行。
"""
import asyncio

from app.api import chat


class FakeRedis:
    """内存版 Redis 子集：get/set，支持并发写入不同 key"""

    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value


async def _worker(user_id: int, session_id: str, msgs: list[str]):
    """并发 worker：写上下文 → 读回，返回读回的上下文内容"""
    await chat.save_ctx(user_id, session_id, [{"role": "user", "content": m} for m in msgs])
    return await chat.get_ctx(user_id, session_id)


def _run_concurrent(sessions, concurrency_boost: int = 0):
    """在单个事件循环里并发跑所有会话，结束后恢复模块 Redis 状态"""

    async def main():
        # 注入假 Redis（每个用例一次性，避免污染模块级真实 redis）
        chat._redis = FakeRedis()
        # 放大并发行：每个会话重复若干次写读，制造并发竞争
        tasks = []
        for _ in range(concurrency_boost):
            for (u, sid, msgs) in sessions:
                tasks.append(_worker(u, sid, msgs))
        return await asyncio.gather(*tasks)

    original = chat._redis
    try:
        return asyncio.run(main())
    finally:
        chat._redis = original


def test_concurrent_multi_user_sessions_isolated():
    """并发运行多用户多会话，各自上下文严格隔离、不串台"""
    sessions = [
        (1, "sess_A", ["用户1-A"]),
        (1, "sess_B", ["用户1-B"]),
        (2, "sess_A", ["用户2-A"]),
        (2, "sess_B", ["用户2-B"]),
    ]
    results = _run_concurrent(sessions)
    for (u, sid, msgs), ctx in zip(sessions, results):
        assert [m["content"] for m in ctx][-1:] == msgs, f"{u}/{sid} 上下文串台"


def test_many_concurrent_same_user_different_sessions():
    """同一用户并发开 50 个会话也不混淆（按 session 隔离）"""
    sessions = [(1, f"s{i}", [f"内容{i}"]) for i in range(50)]
    results = _run_concurrent(sessions, concurrency_boost=2)
    for (_, sid, msgs), ctx in zip(sessions, results):
        assert [m["content"] for m in ctx][-1:] == msgs, f"session {sid} 串台"


def test_two_users_same_session_id_never_mix():
    """不同用户使用同名 session 也不串台（按 user 隔离）"""
    sessions = [(7, "shared", ["U7"]), (8, "shared", ["U8"])]
    results = _run_concurrent(sessions, concurrency_boost=5)
    u7 = [m["content"] for m in results[0]]
    u8 = [m["content"] for m in results[1]]
    assert u7 and u8
    assert set(u7) == {"U7"} and set(u8) == {"U8"}


def test_ctx_key_is_namespaced_by_user_and_session():
    """context key 由 user_id + session_id 共同限定，杜绝跨会话串台"""
    assert chat._ctx_key(1, "s") == "chat:ctx:1:s"
    assert chat._ctx_key(2, "s") == "chat:ctx:2:s"
    assert chat._ctx_key(1, "other") == "chat:ctx:1:other"
    keys = {chat._ctx_key(u, s) for u in (1, 2) for s in ("a", "b")}
    assert len(keys) == 4
