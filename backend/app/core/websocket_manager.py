# WebSocket 连接管理器：管理客户端的长连接，用于流式推送 LLM 输出

from fastapi import WebSocket
from typing import Any
import json


class ConnectionManager:
    def __init__(self):
        # key=client_id, value=WebSocket 连接
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """客户端连上时调用，接受连接并记录"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """客户端断开时调用，移除记录"""
        self.active_connections.pop(client_id, None)

    async def send_json(self, client_id: str, data: dict[str, Any]):
        """给指定客户端发送 JSON 消息"""
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(data, ensure_ascii=False))

    async def send_stream(self, client_id: str, content: str, done: bool = False):
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
