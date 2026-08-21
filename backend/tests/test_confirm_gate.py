"""高危操作确认测试（Claude Code 权限模式）：删/移/执行统一人工确认，无确认通道拒绝"""
import pytest

from app.agents import tools


@pytest.fixture
def tool_map():
    return {t.name: t for t in tools.build_tools(7)}


def test_run_command_requires_confirm(tool_map, monkeypatch):
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", None)
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out


def test_run_command_denied_by_user(tool_map, monkeypatch):
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda cmd, uid, prompt: False)
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out


def test_run_command_approved(tool_map, monkeypatch):
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda cmd, uid, prompt: True)
    out = tool_map["run_command"].invoke({"command": "echo hello"})
    assert "hello" in out


def test_delete_requires_confirm(tool_map, monkeypatch):
    from app.agents import fs_tools
    fs_tools._write_file(7, "conf_del.txt", "keep me")
    monkeypatch.setattr(fs_tools, "_confirm_handler", None)
    out = tool_map["delete_file"].invoke({"file_path": "conf_del.txt"})
    assert "已取消" in out
    assert "keep me" in fs_tools._read_file(7, "conf_del.txt")


def test_move_requires_confirm(tool_map, monkeypatch):
    from app.agents import fs_tools
    fs_tools._write_file(7, "conf_src.txt", "data")
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda cmd, uid, prompt: False)
    out = tool_map["move_file"].invoke({"src_path": "conf_src.txt", "dst_path": "conf_dst.txt"})
    assert "已取消" in out
    assert "conf_src.txt" in fs_tools._list_directory(7, ".")