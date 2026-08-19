"""
聊天路由：WebSocket + Agent + 历史（按会话分组）。
- 认证：WS 握手时校验 ?token= JWT，user_id 由 token 决定（不再信任消息体）
- Origin 校验：防跨站 WebSocket 劫持（CSWSH）
- Redis：缓存会话上下文，key 按 (user_id, session_id) 隔离，杜绝跨会话串台
- 上下文压缩：超过 30 条时把早期消息 LLM 摘要成 system 消息，控制 token 成本
- PostgreSQL chat_history：永久存储，按 session_id 分组
- token 用量统计：每次调用落库 token_usage 表，支撑成本核算
"""
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from langchain_openai import ChatOpenAI
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import LLM_MODEL, DASHSCOPE_API_KEY, REDIS_URL, ALLOWED_ORIGINS
from app.core.database import get_db, async_session
from app.core.security import decode_access_token, get_current_user_id
from app.core.websocket_manager import manager
from app.agents.mcp_agent import agent as mcp_agent
from app.models.chat_message import ChatMessage
from app.models.token_usage import TokenUsage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])

# 北京时间 = UTC + 8
CN_TZ = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(CN_TZ).replace(tzinfo=None)


_llm = None


def _get_llm() -> ChatOpenAI:
    """懒加载 LLM 实例：未配置 API Key 时只在真正使用聊天时才报错，不影响启动"""
    global _llm
    if _llm is None:
        if not DASHSCOPE_API_KEY:
            raise RuntimeError("未配置 DASHSCOPE_API_KEY，请在 backend/.env 中设置")
        _llm = ChatOpenAI(
            model=LLM_MODEL, api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _llm

_redis = None
async def r():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# 上下文压缩参数
CTX_MAX_RAW = 30      # 原始消息超过该条数 → 触发摘要
CTX_KEEP_TAIL = 10    # 摘要后保留的最近消息条数
CTX_MAX_SAVE = 60     # 缓存中最多保存的原始消息条数


def _ctx_key(user_id: int, session_id: str) -> str:
    return f"chat:ctx:{user_id}:{session_id}"


def _sum_key(user_id: int, session_id: str) -> str:
    return f"chat:sum:{user_id}:{session_id}"


async def get_ctx(user_id: int, session_id: str) -> list[dict]:
    data = await (await r()).get(_ctx_key(user_id, session_id))
    return json.loads(data) if data else []


async def save_ctx(user_id: int, session_id: str, ctx: list[dict]):
    await (await r()).set(
        _ctx_key(user_id, session_id),
        json.dumps(ctx[-CTX_MAX_SAVE:], ensure_ascii=False),
        ex=3600,
    )


async def _db_context(user_id: int, session_id: str) -> list[dict]:
    """从 DB 重建会话上下文（切换会话时调用，最多取最近 CTX_MAX_RAW 条）"""
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        msgs = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in msgs][-CTX_MAX_RAW:]


async def _compress(user_id: int, session_id: str, ctx: list[dict]) -> list[dict]:
    """超过上限时对早期消息做 LLM 摘要，返回"摘要 + 最近消息"的有效上下文"""
    if len(ctx) <= CTX_MAX_RAW:
        return ctx
    old, tail = ctx[:-CTX_KEEP_TAIL], ctx[-CTX_KEEP_TAIL:]
    summary_key = _sum_key(user_id, session_id)
    try:
        summary = await (await r()).get(summary_key)
        if not summary:
            text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
            resp = await _get_llm().ainvoke(
                f"请把以下对话压缩成一段 100 字以内的中文摘要，保留关键事实、用户要求和未完成任务：\n{text}"
            )
            summary = (resp.content or "").strip()
            await (await r()).set(summary_key, summary, ex=3600 * 6)
        return [{"role": "system", "content": f"以下是更早对话的摘要：{summary}"}] + tail
    except Exception as e:
        logger.warning("上下文摘要失败，降级为直接截断: %s", e)
        return ctx[-CTX_MAX_RAW:]


async def _record_usage(user_id: int, session_id: str, mode: str, in_tokens: int, out_tokens: int):
    if not (in_tokens or out_tokens):
        return
    async with async_session() as db:
        db.add(TokenUsage(
            user_id=user_id, session_id=session_id, mode=mode,
            model=LLM_MODEL, input_tokens=in_tokens, output_tokens=out_tokens,
        ))
        await db.commit()


# ─── REST：技能列表 ───

@router.get("/skills")
async def list_skills(
    user_id: int = Depends(get_current_user_id),
):
    """返回已安装的技能列表（名称 + SKILL.md 描述），供前端技能面板展示"""
    from app.agents import skill_tools
    root = skill_tools._skills_root()
    if not os.path.isdir(root):
        return []
    skills = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        desc = ""
        skill_md = os.path.join(d, "SKILL.md")
        if os.path.isfile(skill_md):
            with open(skill_md, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(600)
            m = re.search(r"description:\s*[\"']?(.+?)[\"']?\s*$", head, re.M)
            if m:
                desc = m.group(1).strip()
        skills.append({"name": name, "description": desc[:120]})
    return skills


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
    """删除指定会话（同时清掉 Redis 缓存，防止幽灵上下文）"""
    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
        )
    )
    await db.commit()
    try:
        redis = await r()
        await redis.delete(_ctx_key(user_id, session_id), _sum_key(user_id, session_id))
    except Exception:
        pass
    return {"ok": True}


# ─── WebSocket ───

def _handle_confirm_msg(msg: dict, confirm_events: dict, plan_confirm_events: dict) -> None:
    """处理确认类消息（命令确认/规划确认），设置事件供线程侧回调等待"""
    if msg.get("type") == "confirm_response":
        cid = str(msg.get("id", ""))
        if cid in confirm_events:
            evt, box = confirm_events[cid]
            box["allowed"] = bool(msg.get("allow"))
            evt.set()
    elif msg.get("type") == "plan_confirm_response":
        cid = str(msg.get("id", ""))
        if cid in plan_confirm_events:
            evt, box = plan_confirm_events[cid]
            box["allowed"] = bool(msg.get("allow"))
            evt.set()


async def _exec_agent(
    client_id: str,
    user_input: str,
    web_search: bool,
    user_id: int,
    ctx: list[dict] | None,
    use_planning: bool,
):
    """后台执行 Agent（线程池）：工具调用/token 事件经 run_coroutine_threadsafe 回推。
    返回 (reply, used_web_search, in_tokens, out_tokens, tool_names)
    """
    loop = asyncio.get_running_loop()
    usage_box: dict = {}
    tool_names: list[str] = []

    def on_event(evt: dict):
        if evt.get("type") == "usage":
            usage_box.update(evt)
        if evt.get("type") == "tool_call":
            tool_names.append(str(evt.get("name", "")))
        asyncio.run_coroutine_threadsafe(manager.send_json(client_id, evt), loop)

    # 联网搜索开关：强制 Agent 先调用 web_search 获取最新信息再回答
    effective_input = user_input
    if web_search:
        effective_input = (
            f"【联网模式已开启】请先调用 web_search 工具搜索与以下问题相关的最新信息，"
            f"再基于搜索结果组织回答，并注明信息来源。用户问题：{user_input}"
        )

    reply = await asyncio.to_thread(
        mcp_agent.process, effective_input, user_id, ctx, on_event, use_planning
    )

    used_web_search = False
    # 兜底：开启联网但模型未调用 web_search → 强制补一次搜索并追加结果
    if web_search and "web_search" not in tool_names:
        try:
            from app.agents.tools import _web_search
            search_result = _web_search(user_input)
            await manager.send_json(client_id, {
                "type": "tool_call", "name": "web_search", "args": {"query": user_input},
            })
            await manager.send_json(client_id, {
                "type": "tool_result", "name": "web_search", "result": search_result[:400],
            })
            used_web_search = True
            reply = await asyncio.to_thread(
                mcp_agent.process,
                effective_input + "\n\n[搜索结果参考]\n" + search_result,
                user_id, ctx, on_event, use_planning,
            )
        except Exception:
            pass
    elif "web_search" in tool_names:
        used_web_search = True

    # 明确标记本次是否使用了联网搜索（前端据此展示徽标），未用也发送
    await manager.send_json(client_id, {"type": "web_search_used", "used": used_web_search})
    # Agent 回答已由 answer 分片事件推送，这里只发结束标记
    await manager.send_stream(client_id, "", done=True)

    return (
        reply, used_web_search,
        int(usage_box.get("input_tokens") or 0),
        int(usage_box.get("output_tokens") or 0),
        tool_names,
    )

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    # 1. Origin 校验：非白名单来源直接拒绝（防跨站 WebSocket 劫持）
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=4403, reason="Origin not allowed")
        return

    # 2. token 认证：query 参数携带 JWT，user_id 一律从 token 解析，不信任消息体
    user_id = decode_access_token(websocket.query_params.get("token", ""))
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    client_id = uuid.uuid4().hex[:8]
    await manager.connect(client_id, websocket)
    session_id = ""
    current_session = ""
    ctx: list[dict] = []

    # 高危命令人工确认机制：fs_tools 回调 → 推送确认请求到前端 → 等待用户响应
    from app.agents import fs_tools
    confirm_events: dict[str, tuple] = {}
    loop = asyncio.get_running_loop()

    def _await_future(fut, timeout: float):
        """等待线程侧 Future 完成；无论超时/异常都取消底层任务，避免挂起任务泄漏"""
        try:
            return fut.result(timeout=timeout)
        finally:
            fut.cancel()

    def make_confirm_handler():
        def handler(prompt: str) -> bool:
            cid = uuid.uuid4().hex[:12]
            evt = asyncio.Event()
            box = {"allowed": False}
            confirm_events[cid] = (evt, box)
            try:
                _await_future(asyncio.run_coroutine_threadsafe(
                    manager.send_json(client_id, {
                        "type": "confirm_request",
                        "id": cid,
                        "prompt": prompt,
                    }), loop), 5)
                # 等待用户确认（最多 120 秒，超时视为拒绝）
                _await_future(asyncio.run_coroutine_threadsafe(evt.wait(), loop), 120)
                return box["allowed"]
            except Exception:
                return False
            finally:
                confirm_events.pop(cid, None)
        return handler

    fs_tools.set_confirm_handler(make_confirm_handler())

    # 长程规划确认机制：规划器生成计划后推送前端，用户确认才执行
    from app.agents import mcp_agent as mcp_agent_mod
    plan_confirm_events: dict[str, tuple] = {}

    def make_plan_confirm_handler():
        def handler(user_input: str, plan: list[dict]) -> bool:
            cid = uuid.uuid4().hex[:12]
            evt = asyncio.Event()
            box = {"allowed": False}
            plan_confirm_events[cid] = (evt, box)
            try:
                _await_future(asyncio.run_coroutine_threadsafe(
                    manager.send_json(client_id, {
                        "type": "plan_confirm_request",
                        "id": cid,
                        "steps": [{"name": p["name"], "action": p["action"]} for p in plan],
                    }), loop), 5)
                _await_future(asyncio.run_coroutine_threadsafe(evt.wait(), loop), 180)
                return box["allowed"]
            except Exception:
                return False
            finally:
                plan_confirm_events.pop(cid, None)
        return handler

    mcp_agent_mod.set_plan_confirm_handler(make_plan_confirm_handler())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # 高危命令人工确认响应：设置事件供 fs_tools 确认回调等待
            if msg.get("type") in ("confirm_response", "plan_confirm_response"):
                _handle_confirm_msg(msg, confirm_events, plan_confirm_events)
                continue

            user_input = msg.get("message", "")
            use_agent = msg.get("use_agent", False)
            web_search = bool(msg.get("web_search", False))
            use_planning = bool(msg.get("use_planning", False))
            logger.info("[WS] 收到消息 user=%s 会话=%s agent=%s 联网=%s 规划=%s 内容=%s",
                        user_id, session_id, use_agent, web_search, use_planning, user_input[:120])
            session_id = msg.get("session_id") or current_session or uuid.uuid4().hex[:16]

            # 会话切换 → 从 DB 重建上下文（杜绝跨会话串台）
            if session_id != current_session:
                current_session = session_id
                ctx = await _db_context(user_id, session_id)

            # 保存用户消息
            async with async_session() as db:
                db.add(ChatMessage(user_id=user_id, session_id=session_id, created_at=now_cn(),
                                   role="user", content=user_input))
                await db.commit()

            ctx.append({"role": "user", "content": user_input})
            effective = await _compress(user_id, session_id, ctx)

            in_tokens = out_tokens = 0
            reply = ""
            used_web_search = False
            if use_agent or web_search:
                # Agent 模式：后台任务执行（不阻塞事件循环），同时并发监听 WebSocket，
                # 用户对高危命令/执行计划的确认响应能立即送达（此前主循环被 to_thread 阻塞，
                # 确认响应积压导致每次都要干等 120 秒超时）
                agent_task = asyncio.create_task(
                    _exec_agent(client_id, user_input, web_search, user_id, effective[:-1], use_planning)
                )
                ws_task = asyncio.create_task(websocket.receive_text())
                while True:
                    done, _ = await asyncio.wait(
                        {agent_task, ws_task}, return_when=asyncio.FIRST_COMPLETED
                    )
                    if agent_task in done:
                        if ws_task in done:
                            try:
                                _handle_confirm_msg(json.loads(ws_task.result()),
                                                    confirm_events, plan_confirm_events)
                            except Exception:
                                pass
                        else:
                            ws_task.cancel()
                        (reply, used_web_search, in_tokens, out_tokens, tool_names) = agent_task.result()
                        logger.info("[WS] Agent 回复完成 user=%s 工具调用=%s 回复长度=%s",
                                    user_id, tool_names, len(reply))
                        break
                    # Agent 执行期间收到 WS 消息：仅处理确认类，其余忽略
                    msg2 = json.loads(ws_task.result())
                    if msg2.get("type") in ("confirm_response", "plan_confirm_response"):
                        _handle_confirm_msg(msg2, confirm_events, plan_confirm_events)
                    else:
                        logger.info("[WS] Agent 执行中忽略非确认消息: %s", str(msg2)[:80])
                    ws_task = asyncio.create_task(websocket.receive_text())
            else:
                full_reply = ""
                for chunk in _get_llm().stream(effective):
                    content = chunk.content or ""
                    full_reply += content
                    um = getattr(chunk, "usage_metadata", None) or {}
                    in_tokens = um.get("input_tokens", in_tokens) or in_tokens
                    out_tokens = um.get("output_tokens", out_tokens) or out_tokens
                    await manager.send_stream(client_id, content, done=False)
                await manager.send_stream(client_id, "", done=True)
                reply = full_reply

            ctx.append({"role": "assistant", "content": reply})
            await save_ctx(user_id, session_id, ctx)
            await _record_usage(user_id, session_id, "agent" if use_agent else "chat",
                                in_tokens, out_tokens)

            async with async_session() as db:
                db.add(ChatMessage(user_id=user_id, session_id=session_id, created_at=now_cn(),
                                   role="assistant", content=reply))
                await db.commit()

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        logger.exception("WebSocket 处理异常，连接已关闭")
        manager.disconnect(client_id)
