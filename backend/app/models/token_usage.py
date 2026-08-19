# token 用量统计模型：记录每次 LLM 调用的 token 消耗，支撑成本核算
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)   # 归属用户
    session_id = Column(String(32), default="")             # 所属会话
    mode = Column(String(16), default="chat")               # chat / agent
    model = Column(String(64), default="")                  # 模型名
    input_tokens = Column(Integer, default=0)               # 输入 token
    output_tokens = Column(Integer, default=0)              # 输出 token
    created_at = Column(DateTime, default=datetime.utcnow)
