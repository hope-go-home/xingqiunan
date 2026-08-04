# 用户模型：对应数据库 users 表

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)        # 主键，自增
    username = Column(String(64), unique=True, nullable=False, index=True)  # 用户名，唯一索引
    hashed_password = Column(String(256), nullable=False)             # bcrypt 加密后的密码
    created_at = Column(DateTime, default=datetime.utcnow)            # 注册时间
