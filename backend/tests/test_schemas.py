"""Schema 校验测试：注册/登录入参边界"""
import pytest
from pydantic import ValidationError

from app.schemas.user import RegisterRequest


def test_register_ok():
    req = RegisterRequest(username="alice", password="secret123")
    assert req.username == "alice"


def test_register_blank_username_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(username="   ", password="secret123")


def test_register_short_password_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(username="alice", password="12345")


def test_register_username_trimmed():
    req = RegisterRequest(username="  bob  ", password="secret123")
    assert req.username == "bob"
