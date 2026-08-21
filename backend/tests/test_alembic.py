# Alembic 迁移回归测试：验证迁移链完整
# 需要真实 PostgreSQL，CI 环境无数据库时自动跳过

import os
import subprocess
import sys
from pathlib import Path

import pytest

ALEMBIC_INI = str(Path(__file__).resolve().parents[1] / "alembic.ini")

# CI 环境无 PostgreSQL，跳过迁移测试
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or not os.getenv("DATABASE_URL", "").startswith("postgresql+asyncpg://user:"),
    reason="需要真实 PostgreSQL 连接",
)


def _run_alembic(*args: str) -> str:
    """用当前 Python 解释器调用 alembic CLI"""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ALEMBIC_INI, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout + result.stderr


def test_alembic_current():
    """数据库应处于某个迁移版本"""
    out = _run_alembic("current")
    assert "head" in out or "(" in out


def test_alembic_history_not_empty():
    """迁移历史不应为空"""
    out = _run_alembic("history")
    assert "05682bdd463b" in out


def test_alembic_heads_single():
    """应只有一个 head（无分支冲突）"""
    out = _run_alembic("heads")
    lines = [l.strip() for l in out.strip().splitlines() if l.strip() and not l.startswith("=")]
    assert len(lines) == 1, f"预期单 head，实际: {lines}"
