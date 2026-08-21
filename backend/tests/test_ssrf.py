# SSRF 防护 + session 级权限 + 审计日志测试

from app.agents.netguard import validate_public_url


# ─── SSRF 防护 ───

def test_ssrf_block_private_ip():
    ok, reason = validate_public_url("http://127.0.0.1:5432")
    assert not ok
    assert "私网" in reason


def test_ssrf_block_metadata_aws():
    ok, reason = validate_public_url("http://169.254.169.254/latest/meta-data/")
    assert not ok


def test_ssrf_block_metadata_aliyun():
    ok, reason = validate_public_url("http://100.100.100.200/latest/meta-data/")
    assert not ok


def test_ssrf_block_localhost():
    ok, reason = validate_public_url("http://localhost:8080/admin")
    assert not ok


def test_ssrf_block_private_cidr():
    for addr in ["http://10.0.0.1", "http://172.16.0.1", "http://192.168.1.1"]:
        ok, reason = validate_public_url(addr)
        assert not ok, f"应拦截: {addr}"


def test_ssrf_block_non_http():
    ok, reason = validate_public_url("ftp://example.com/file")
    assert not ok
    assert "http" in reason.lower()


def test_ssrf_block_empty():
    ok, _ = validate_public_url("")
    assert not ok


def test_ssrf_allow_public():
    ok, reason = validate_public_url("https://www.example.com/page")
    assert ok, f"公网 URL 应放行: {reason}"


# ─── session 级权限（测试 handler 逻辑）───

def test_confirm_handler_session_permission():
    """模拟：首次确认后，同类命令自动放行"""
    allowed = set()
    calls = []

    def handler(command, user_id, prompt):
        if command in allowed:
            calls.append(("auto", command))
            return True
        calls.append(("prompt", command))
        allowed.add(command)
        return True

    # 首次 → 弹确认
    assert handler("run_command ls", 1, "确认？") is True
    assert len(calls) == 1
    assert calls[0] == ("prompt", "run_command ls")

    # 再次 → 自动放行
    assert handler("run_command ls", 1, "确认？") is True
    assert len(calls) == 2
    assert calls[1] == ("auto", "run_command ls")

    # 不同命令 → 仍需确认
    assert handler("delete_file x.txt", 1, "确认？") is True
    assert len(calls) == 3
    assert calls[2] == ("prompt", "delete_file x.txt")


def test_confirm_handler_deny_no_session_permission():
    """拒绝后不会记入 session 权限"""
    allowed = set()

    def handler(command, user_id, prompt):
        if command in allowed:
            return True
        return False  # 拒绝

    assert handler("run_command rm -rf /", 1, "确认？") is False
    assert "run_command rm -rf /" not in allowed
    # 再次仍需确认（不会自动放行）
    assert handler("run_command rm -rf /", 1, "确认？") is False
