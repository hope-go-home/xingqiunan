"""审计与工具注册表测试：审计 JSONL 落盘/脱敏、工具注册完整性"""
import json

import pytest

import app.agents.tools as tools


@pytest.fixture()
def audit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", str(tmp_path))
    return tmp_path


def _read_audit(audit_dir):
    p = audit_dir / "audit" / "tool_calls.jsonl"
    assert p.is_file()
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]


def test_audit_writes_jsonl(audit_dir):
    tools._audit_write(7, "write_file", ("demo.txt",), {"content": "hi"}, "已写入", 0.012)
    recs = _read_audit(audit_dir)
    assert len(recs) == 1
    r = recs[0]
    assert r["user_id"] == 7
    assert r["tool"] == "write_file"
    assert r["duration_s"] == 0.012
    assert "demo.txt" in json.dumps(r["args"], ensure_ascii=False)


def test_audit_truncates_long_args(audit_dir):
    """长参数/长结果被截断，防止审计日志膨胀"""
    tools._audit_write(7, "write_file", (), {"content": "x" * 5000}, "y" * 5000, 0.1)
    r = _read_audit(audit_dir)[0]
    assert len(r["args"]["kw"]["content"]) <= 310
    assert len(r["result"]) <= 500


def test_audit_failure_does_not_break(audit_dir, monkeypatch):
    """审计写失败不影响功能"""
    monkeypatch.setattr(tools.os, "makedirs", lambda *a, **k: (_ for _ in ()).throw(OSError("denied")))
    tools._audit_write(7, "tool_x", (), {}, "ok", 0.0)  # 不抛异常


def test_build_tools_registration_complete():
    """工具注册表与定义一致：21 个（Claude Code 模式：高危工具全员注册，普通用户逐次确认）"""
    names = {t.name for t in tools.build_tools(7, role="admin")}
    assert len(names) == 21
    expected = {
        "parse_document", "list_directory", "list_tasks", "translate", "create_task",
        "search_knowledge", "add_knowledge", "analyze_image", "ocr_image", "speech_to_text",
        "web_search", "write_file", "read_file", "list_workspace", "create_directory",
        "delete_file", "move_file", "run_command", "install_skill", "list_skills", "load_skill",
    }
    assert names == expected
    user_names = {t.name for t in tools.build_tools(7, role="user")}
    assert user_names == expected  # 普通用户同样拥有全部工具，仅高危操作需确认


def test_build_tools_schemas_intact():
    """审计装饰器不破坏 LangChain 工具签名（schema 参数完整）"""
    tools_map = {t.name: t for t in tools.build_tools(7, role="admin")}
    write_file = tools_map["write_file"]
    schema = write_file.args_schema
    assert "file_path" in schema.model_fields and "content" in schema.model_fields
    run_command = tools_map["run_command"]
    assert "command" in run_command.args_schema.model_fields


def test_audited_tools_record_real_calls(audit_dir, tmp_path, monkeypatch):
    """真实调用带审计装饰器的工具会落审计（用无外部依赖的工具，CI 无密钥也能跑）"""
    import app.agents.tools as t
    monkeypatch.setattr(t, "LOG_DIR", str(audit_dir))
    tools_map = {x.name: x for x in tools.build_tools(7)}
    out = tools_map["list_workspace"].invoke({"dir_path": "."})
    assert isinstance(out, str) and out
    recs = _read_audit(audit_dir)
    assert any(r["tool"] == "list_workspace" and r["user_id"] == 7 for r in recs)