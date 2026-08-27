# 任务请求/响应体

from pydantic import BaseModel
from datetime import datetime


class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    title: str
    description: str = ""
    task_type: str = ""


class TaskResponse(BaseModel):
    """任务信息响应"""
    id: int
    title: str
    description: str
    status: str
    task_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
