# 聊天接口的请求/响应体

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """聊天请求：用户发送的消息"""
    message: str
    session_id: Optional[str] = None
    use_agent: bool = False  # True 走 MCP Agent，False 走普通 LLM 对话


class ChatResponse(BaseModel):
    """聊天响应：助手回复的内容"""
    reply: str
    session_id: str
