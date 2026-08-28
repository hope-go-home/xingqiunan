"""高危操作确认测试（Claude Code 权限模式）：删/移/执行统一人工确认，无确认通道拒绝"""
import pytest

from app.agents import tools, fs_tools


@pytest.fixture
def tool_map():
    return {t.name: t for t in tools.build_tools(7)}


def test_run_command_requires_confirm(tool_map, monkeypatch):
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out


def test_run_command_denied_by_user(tool_map, monkeypatch):
    fs_tools.set_confirm_handler(lambda cmd, uid, prompt: False, user_id=7)
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out
    fs_tools.remove_confirm_handler(7)


def test_run_command_approved(tool_map, monkeypatch):
    fs_tools.set_confirm_handler(lambda cmd, uid, prompt: True, user_id=7)
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "hello" in out
    fs_tools.remove_confirm_handler(7)


def test_delete_requires_confirm(tool_map, monkeypatch):
    fs_tools._write_file(7, "conf_del.txt", "keep me")
    out = tool_map["delete_file"].invoke({"file_path": "conf_del.txt"})
    assert "已取消" in out
    assert "keep me" in fs_tools._read_file(7, "conf_del.txt")


def test_move_requires_confirm(tool_map, monkeypatch):
    fs_tools._write_file(7, "conf_src.txt", "data")
    fs_tools.set_confirm_handler(lambda cmd, uid, prompt: False, user_id=7)
    out = tool_map["move_file"].invoke({"src_path": "conf_src.txt", "dst_path": "conf_dst.txt"})
    assert "已取消" in out
    assert "conf_src.txt" in fs_tools._list_directory(7, ".")
    fs_tools.remove_confirm_handler(7)