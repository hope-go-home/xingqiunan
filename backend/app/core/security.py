# 安全模块：密码加密 + JWT 令牌生成与验证

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import SECRET_KEY as _SECRET_KEY

# JWT 签名密钥和算法（从 .env 读取，不再硬编码）
SECRET_KEY = _SECRET_KEY
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
    """登录成功时调用：生成 JWT，编码 user_id，24 小时过期"""
    expire = datetime.now(timezone.utc) + timedelta(days=1)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# HTTP Bearer Token 提取器，自动从请求头 Authorization: Bearer xxx 中取出 token
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    依赖注入函数，解析 JWT 返回当前用户 ID。
    路由里声明 user_id: int = Depends(get_current_user_id) 即可拿到登录用户 ID。
    如果 token 无效或过期，直接返回 401。
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
