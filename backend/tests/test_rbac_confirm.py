"""Claude Code 权限模式测试：高危工具全员注册，普通用户逐次确认，无确认通道拒绝"""
import pytest

from app.agents import tools


@pytest.fixture
def user_tools():
    return {t.name: t for t in tools.build_tools(7, role="user")}


def test_non_admin_run_command_requires_confirm(user_tools, monkeypatch):
    """普通用户执行命令：无确认通道 → 拒绝且命令不执行"""
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", None)
    out = user_tools["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out


def test_non_admin_run_command_denied_by_user(user_tools, monkeypatch):
    """普通用户执行命令：用户拒绝 → 取消"""
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda prompt: False)
    out = user_tools["run_command"].invoke({"command": "echo hello"})
    assert "已取消" in out


def test_non_admin_run_command_approved(user_tools, monkeypatch):
    """普通用户执行命令：用户允许 → 执行（白名单内命令）"""
    from app.agents import fs_tools
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda prompt: True)
    out = user_tools["run_command"].invoke({"command": "echo hello"})
    assert "hello" in out


def test_non_admin_delete_requires_confirm(user_tools, monkeypatch):
    """普通用户删除文件：未确认 → 文件仍在"""
    from app.agents import fs_tools
    fs_tools._write_file("rbac_del.txt", "keep me")
    monkeypatch.setattr(fs_tools, "_confirm_handler", None)
    out = user_tools["delete_file"].invoke({"file_path": "rbac_del.txt"})
    assert "已取消" in out
    content = fs_tools._read_file("rbac_del.txt")
    assert "keep me" in content


def test_non_admin_move_requires_confirm(user_tools, monkeypatch):
    """普通用户移动文件：用户拒绝 → 文件保持原位"""
    from app.agents import fs_tools
    fs_tools._write_file("rbac_move_src.txt", "data")
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda prompt: False)
    out = user_tools["move_file"].invoke({"src_path": "rbac_move_src.txt", "dst_path": "rbac_move_dst.txt"})
    assert "已取消" in out
    assert "rbac_move_src.txt" in fs_tools._list_directory(".")


def test_admin_run_command_no_confirm_needed(monkeypatch):
    """admin 执行白名单内安全命令：不弹确认直接执行"""
    from app.agents import fs_tools
    admin_tools = {t.name: t for t in tools.build_tools(7, role="admin")}
    calls = []
    monkeypatch.setattr(fs_tools, "_confirm_handler", lambda prompt: calls.append(prompt) or True)
    out = admin_tools["run_command"].invoke({"command": "echo admin-ok"})
    assert "admin-ok" in out
    assert calls == []  # 白名单安全命令无需确认