# 用户请求/响应体：定义 API 的输入输出格式

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    """注册请求：校验用户名不为空、密码至少 6 位"""
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("用户名不能为空")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少6位")
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应：只暴露 id 和 username，不返回密码"""
    id: int
    username: str

    model_config = {"from_attributes": True}  # 支持从 ORM 模型转换


class TokenResponse(BaseModel):
    """登录成功响应：返回 JWT 令牌 + 用户信息"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
