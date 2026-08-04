# 认证路由：/auth/register 注册、/auth/login 登录

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户，用户名重复返回 400"""
    service = AuthService(db)
    try:
        return await service.register(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，成功返回 JWT 令牌 + 用户信息"""
    service = AuthService(db)
    try:
        return await service.login(req)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
