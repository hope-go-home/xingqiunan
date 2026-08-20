"""多租户隔离测试：用户工作区互相不可见，路径越界一律拒绝"""
import os

import pytest

from app.agents import fs_tools
from app.core.config import WORKSPACE_DIR


def test_users_isolated_workspaces():
    """用户 A 写入的文件在用户 B 的工作区不可见"""
    fs_tools._write_file(1, "a.txt", "user1 data")
    fs_tools._write_file(2, "a.txt", "user2 data")
    assert "user1 data" in fs_tools._read_file(1, "a.txt")
    assert "user2 data" in fs_tools._read_file(2, "a.txt")
    # 用户 1 无法读取用户 2 的文件（路径越界）
    with pytest.raises(ValueError, match="越界"):
        fs_tools._read_file(1, "../user_2/a.txt")
    # 用户 1 的工作区只看到自己的文件
    listing_1 = fs_tools._list_directory(1)
    assert "a.txt" in listing_1
    assert "user_2" not in listing_1


def test_cross_user_path_rejected():
    """相对路径穿越到他人工作区 → 越界拒绝"""
    fs_tools._write_file(2, "notes.txt", "s")
    with pytest.raises(ValueError, match="越界"):
        fs_tools._read_file(1, "../user_2/notes.txt")


def test_absolute_path_to_other_user_cannot_read():
    """绝对路径指向他人工作区：不会读到他人文件（取文件名映射回自己工作区）"""
    fs_tools._write_file(3, "x.txt", "user3 data")
    fs_tools._write_file(1, "x.txt", "user1 data")
    out = fs_tools._read_file(1, fs_tools._user_workspace(3) + "/x.txt")
    assert "user3 data" not in out
    assert "user1 data" in out


def test_user_workspace_under_global_root():
    """用户工作区 = WORKSPACE_DIR/user_{id}，与 skills 共享区平级"""
    root = os.path.realpath(WORKSPACE_DIR)
    u1 = os.path.realpath(fs_tools._user_workspace(1))
    skills = os.path.realpath(os.path.join(root, "skills"))
    assert u1.startswith(root + os.sep)
    assert u1 != skills  # 用户私有区 ≠ 技能共享区
    assert u1 == os.path.realpath(os.path.join(root, "user_1"))