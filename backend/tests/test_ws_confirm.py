"""WS 确认流测试：命令确认/规划确认消息处理（纯函数逻辑）"""
import asyncio

from app.api.chat import _handle_confirm_msg


def test_confirm_response_sets_event():
    evt = asyncio.Event()
    box = {"allowed": False}
    confirm_events = {"abc123": (evt, box)}
    _handle_confirm_msg({"type": "confirm_response", "id": "abc123", "allow": True},
                        confirm_events, {}, {})
    assert box["allowed"] is True
    assert evt.is_set()


def test_confirm_response_deny():
    evt = asyncio.Event()
    box = {"allowed": True}
    _handle_confirm_msg({"type": "confirm_response", "id": "x", "allow": False},
                        {"x": (evt, box)}, {}, {})
    assert box["allowed"] is False
    assert evt.is_set()


def test_plan_confirm_response_sets_event():
    evt = asyncio.Event()
    box = {"allowed": False}
    _handle_confirm_msg({"type": "plan_confirm_response", "id": "plan1", "allow": True},
                        {}, {"plan1": (evt, box)}, {})
    assert box["allowed"] is True
    assert evt.is_set()


def test_unknown_id_ignored():
    evt = asyncio.Event()
    box = {"allowed": False}
    _handle_confirm_msg({"type": "confirm_response", "id": "ghost", "allow": True},
                        {"real": (evt, box)}, {}, {})
    assert not evt.is_set()
    assert box["allowed"] is False


def test_non_confirm_message_ignored():
    _handle_confirm_msg({"type": "answer", "content": "hi"}, {}, {}, {})  # 不抛异常