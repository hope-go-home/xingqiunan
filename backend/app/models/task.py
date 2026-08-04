# 任务模型：对应数据库 tasks 表，记录用户提交的自动化任务

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)        # 主键
    title = Column(String(256), nullable=False)                       # 任务名称
    description = Column(Text, default="")                            # 任务描述
    status = Column(String(32), default="pending")                    # pending → running → completed / failed
    task_type = Column(String(64), default="")                        # 任务分类：document_process / data_calc / file_convert
    user_id = Column(Integer, nullable=False)                         # 创建者 ID
    created_at = Column(DateTime, default=datetime.utcnow)            # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
