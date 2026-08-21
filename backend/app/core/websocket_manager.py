# WebSocket 连接管理器：Redis Pub/Sub 跨实例路由
# 单实例：内存 dict 直连
# 多实例：Redis Pub/Sub 广播，每台实例只推给自己连接的用户

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import REDIS_URL

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # 本地连接表：key=user_id, value=WebSocket
        self._local: dict[str, WebSocket] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._instance_id: str = ""

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                REDIS_URL, decode_responses=True, max_connections=10,
            )
        return self._redis

    # ─── 连接管理 ───

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._local[user_id] = websocket
        logger.info("[WS] 用户 %s 已连接（本实例）", user_id)

        # 首次连接时启动 Redis 订阅监听
        if self._listener_task is None:
            await self._start_listener()

    def disconnect(self, user_id: str):
        self._local.pop(user_id, None)
        logger.info("[WS] 用户 %s 已断开（本实例）", user_id)

    # ─── Redis Pub/Sub：跨实例消息路由 ───

    async def _start_listener(self):
        """启动 Redis 订阅监听：收到消息后推给本地连接的用户"""
        try:
            r = await self._get_redis()
            self._pubsub = r.pubsub()
            await self._pubsub.psubscribe("ws:*")
            self._listener_task = asyncio.create_task(self._listen_loop())
            logger.info("[WS] Redis Pub/Sub 监听已启动")
        except Exception as e:
            logger.warning("[WS] Redis Pub/Sub 启动失败，退化为单实例模式: %s", e)

    async def _listen_loop(self):
        """持续监听 Redis 频道，收到消息推给本地用户"""
        try:
            async for msg in self._pubsub.listen():
                if msg["type"] != "pmessage":
                    continue
                channel = msg["channel"]  # 格式: ws:{user_id}
                user_id = channel.split(":", 1)[1] if ":" in channel else ""
                if user_id in self._local:
                    try:
                        payload = json.loads(msg["data"])
                        ws = self._local[user_id]
                        await ws.send_text(json.dumps(payload, ensure_ascii=False))
                    except Exception as e:
                        logger.warning("[WS] 推送给 %s 失败: %s", user_id, e)
                        self._local.pop(user_id, None)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[WS] Redis 监听异常: %s", e)

    async def send_json(self, user_id: str, data: dict[str, Any]):
        """发送 JSON 消息：优先本地直推，本地没有则走 Redis Pub/Sub"""
        if user_id in self._local:
            try:
                await self._local[user_id].send_text(
                    json.dumps(data, ensure_ascii=False)
                )
                return
            except Exception:
                self._local.pop(user_id, None)

        # 本地没有 → 发到 Redis，让其他实例投递
        try:
            r = await self._get_redis()
            await r.publish(f"ws:{user_id}", json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("[WS] Redis publish 失败: %s", e)

    async def send_stream(self, user_id: str, content: str, done: bool = False):
        await self.send_json(user_id, {"type": "stream", "content": content, "done": done})

    async def broadcast(self, data: dict[str, Any]):
        """广播：发到 Redis 广播频道，所有实例都收"""
        try:
            r = await self._get_redis()
            await r.publish("ws:broadcast", json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("[WS] broadcast 失败: %s", e)

    async def shutdown(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe()
        if self._redis:
            await self._redis.close()


# 全局单例
manager = ConnectionManager()
