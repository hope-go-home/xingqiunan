"""认证与令牌安全测试：JWT 编解码、密钥隔离、密码哈希"""
import jwt

from app.core import security


def test_token_roundtrip():
    uid = 42
    token = security.create_access_token(uid)
    assert security.decode_access_token(token) == uid


def test_token_tampered_returns_none():
    token = security.create_access_token(1)
    bad = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert security.decode_access_token(bad) is None


def test_token_wrong_key_returns_none():
    token = jwt.encode({"sub": "1"}, "some-other-secret", algorithm="HS256")
    assert security.decode_access_token(token) is None


def test_token_requires_sub():
    token = jwt.encode({"exp": 9999999999}, security.SECRET_KEY, algorithm="HS256")
    assert security.decode_access_token(token) is None


def test_password_hash_roundtrip():
    hashed = security.hash_password("secret123")
    assert hashed != "secret123"
    assert security.verify_password("secret123", hashed)
    assert not security.verify_password("wrong", hashed)


def test_two_hashes_differ():
    # bcrypt 加盐：同一密码两次哈希结果不同
    assert security.hash_password("same") != security.hash_password("same")
