# 安全模块：密码加密 + JWT 令牌生成与验证
# 密钥/过期时间统一从 app.core.config 读取（.env 可配），不再硬编码

import logging
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

# bcrypt 加密工具，schemes=["bcrypt"] 指定使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """注册时调用：明文 → bcrypt 密文，不可逆"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """登录时调用：比对明文和密文是否匹配"""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """登录成功时调用：生成 JWT，编码 user_id，过期时间由配置决定（默认 24 小时）"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """解析 JWT，返回 user_id；token 无效/过期返回 None（不抛异常）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError):
        return None


# HTTP Bearer Token 提取器，自动从请求头 Authorization: Bearer xxx 中取出 token
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    依赖注入函数，解析 JWT 返回当前用户 ID。
    路由里声明 user_id: int = Depends(get_current_user_id) 即可拿到登录用户 ID。
    如果 token 无效或过期，直接返回 401。
    """
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id
