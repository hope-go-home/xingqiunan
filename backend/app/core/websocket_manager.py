# WebSocket 连接管理器：管理客户端的长连接，用于流式推送 LLM 输出
# 单实例部署：内存直推（零开销、零外部依赖）
# 说明：曾尝试 Redis Pub/Sub 跨实例路由，实测在单实例场景下引入
# 不稳定因素（监听连接超时），且当前无多实例需求，故回退为简单实现。

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # key=用户标识（user_id 即可，int/str 均可）, value=WebSocket 连接
        self.active_connections: dict[Any, WebSocket] = {}

    async def connect(self, client_id: Any, websocket: WebSocket):
        """客户端连上时调用，接受连接并记录"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: Any):
        """客户端断开时调用，移除记录"""
        self.active_connections.pop(client_id, None)

    async def send_json(self, client_id: Any, data: dict[str, Any]):
        """给指定客户端发送 JSON 消息"""
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(data, ensure_ascii=False))

    async def send_stream(self, client_id: Any, content: str, done: bool = False):
        """
        发送流式文本块，用于 LLM 逐字输出。
        done=True 表示本次流结束，前端停止等待。
        """
        await self.send_json(client_id, {"type": "stream", "content": content, "done": done})

    async def broadcast(self, data: dict[str, Any]):
        """广播消息给所有连接的客户端"""
        for ws in self.active_connections.values():
            await ws.send_text(json.dumps(data, ensure_ascii=False))


# 全局单例，所有地方用 manager 即可
manager = ConnectionManager()
