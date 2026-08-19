# 认证业务逻辑：注册和登录

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import RegisterRequest, LoginRequest, UserResponse, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: RegisterRequest) -> UserResponse:
        # 1. 检查用户名是否已存在
        result = await self.db.execute(select(User).where(User.username == req.username))
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 2. 创建用户（密码加密后入库）；第一个注册用户自动成为管理员
        user_count = (await self.db.execute(select(User.id))).scalars().all()
        role = "admin" if not user_count else "user"
        user = User(username=req.username, hashed_password=hash_password(req.password), role=role)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)  # 刷新获取自增 id
        return UserResponse.model_validate(user)

    async def login(self, req: LoginRequest) -> TokenResponse:
        # 1. 按用户名查用户
        result = await self.db.execute(select(User).where(User.username == req.username))
        user = result.scalar_one_or_none()
        # 2. 验证密码（返回统一错误，不暴露哪个错了）
        if not user or not verify_password(req.password, user.hashed_password):
            raise ValueError("用户名或密码错误")

        # 3. 生成 JWT 令牌并返回（令牌携带角色，权限在服务端各环节校验）
        token = create_access_token(user.id, user.role)
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
