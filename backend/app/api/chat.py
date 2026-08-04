"""
聊天路由：WebSocket + Agent + 历史（按会话分组）。
- Redis：缓存当前会话上下文，1 小时过期
- PostgreSQL chat_history：永久存储，按 session_id 分组
"""
import uuid
import json
import asyncio
from datetime import datetime, timedelta, timezone
import redis.asyncio as aioredis

# 北京时间 = UTC + 8
CN_TZ = timezone(timedelta(hours=8))

def now_cn():
    return datetime.now(CN_TZ).replace(tzinfo=None)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, delete, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI

from app.core.database import get_db, async_session
from app.core.security import get_current_user_id
from app.core.websocket_manager import manager
from app.core.config import LLM_MODEL, DASHSCOPE_API_KEY, REDIS_URL
from app.agents.mcp_agent import agent as mcp_agent
from app.models.chat_message import ChatMessage

router = APIRouter(prefix="/chat", tags=["聊天"])

llm = ChatOpenAI(
    model=LLM_MODEL, api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

_redis = None
async def r(): global _redis; _redis = _redis or aioredis.from_url(REDIS_URL, decode_responses=True); return _redis

async def get_ctx(user_id: int, session_id: str) -> list[dict]:
    data = await (await r()).get(f"chat:ctx:{user_id}:{session_id}")
    return json.loads(data) if data else []

async def save_ctx(user_id: int, session_id: str, ctx: list[dict]):
    await (await r()).set(f"chat:ctx:{user_id}:{session_id}", json.dumps(ctx[-20:], ensure_ascii=False), ex=3600)


# ─── REST：会话列表 ───

@router.get("/sessions")
async def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """返回用户的所有会话摘要（每个 session 的第一条用户消息作为标题）"""
    result = await db.execute(
        select(ChatMessage.session_id, ChatMessage.content, ChatMessage.created_at)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
        .order_by(ChatMessage.session_id, ChatMessage.id.asc())
    )
    rows = result.all()

    seen = {}
    for sid, content, ts in rows:
        if sid not in seen:
            seen[sid] = {"session_id": sid, "title": content[:40], "time": ts.strftime("%m-%d %H:%M")}

    sessions = list(seen.values())
    sessions.reverse()
    return sessions


# ─── REST：会话消息 ───

@router.get("/history")
async def load_history(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """加载指定会话的全部消息"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
    )
    return [{"id": m.id, "role": m.role, "content": m.content,
             "time": m.created_at.strftime("%H:%M")}
            for m in result.scalars().all()]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """删除指定会话"""
    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
        )
    )
    await db.commit()
    return {"ok": True}


# ─── WebSocket ───

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    client_id = uuid.uuid4().hex[:8]
    await manager.connect(client_id, websocket)
    user_id = 0
    session_id = ""

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            user_input = msg.get("message", "")
            use_agent = msg.get("use_agent", False)
            user_id = msg.get("user_id", user_id)
            session_id = msg.get("session_id", session_id) or uuid.uuid4().hex[:16]

            # 保存用户消息
            if user_id:
                async with async_session() as db:
                    db.add(ChatMessage(user_id=user_id, session_id=session_id, created_at=now_cn(),
                                       role="user", content=user_input))
                    await db.commit()

            ctx = await get_ctx(user_id, session_id)
            ctx.append({"role": "user", "content": user_input})

            reply = ""
            if use_agent:
                # Agent 模式：丢线程池执行（不阻塞事件循环），
                # 工具调用事件经 run_coroutine_threadsafe 回推 WebSocket
                loop = asyncio.get_running_loop()

                def on_event(evt: dict):
                    asyncio.run_coroutine_threadsafe(
                        manager.send_json(client_id, evt), loop
                    )

                reply = await asyncio.to_thread(
                    mcp_agent.process, user_input, user_id, ctx[:-1], on_event
                )
                # Agent 回答已由 answer 分片事件推送，这里只发结束标记
                await manager.send_stream(client_id, "", done=True)
                ctx.append({"role": "assistant", "content": reply})
                await save_ctx(user_id, session_id, ctx)
            else:
                full_reply = ""
                for chunk in llm.stream(ctx):
                    content = chunk.content or ""
                    full_reply += content
                    await manager.send_stream(client_id, content, done=False)
                await manager.send_stream(client_id, "", done=True)
                ctx.append({"role": "assistant", "content": full_reply})
                await save_ctx(user_id, session_id, ctx)

            if user_id:
                async with async_session() as db:
                    db.add(ChatMessage(user_id=user_id, session_id=session_id, created_at=now_cn(),
                                       role="assistant", content=reply if use_agent else full_reply))
                    await db.commit()

    except WebSocketDisconnect:
        manager.disconnect(client_id)
