"""聊天历史模型：chat_history 表，按 session 分组。"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timedelta, timezone
from app.core.database import Base

CN_TZ = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(CN_TZ).replace(tzinfo=None)


class ChatMessage(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(32), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, default="")
    created_at = Column(DateTime, default=now_cn)
