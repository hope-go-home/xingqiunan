"""WS 停止流测试：stop 消息处理（纯函数逻辑）"""
import asyncio

from app.api.chat import _handle_confirm_msg


def test_stop_message_does_not_touch_confirm_events():
    """stop 消息不属于确认类，不应触发确认事件"""
    evt = asyncio.Event()
    box = {"allowed": False}
    _handle_confirm_msg({"type": "stop"}, {"abc": (evt, box)}, {}, {})
    assert not evt.is_set()
    assert box["allowed"] is False


def test_stop_message_tolerated_with_empty_registries():
    """停止消息在无任何挂起确认时也不抛异常"""
    _handle_confirm_msg({"type": "stop"}, {}, {}, {})