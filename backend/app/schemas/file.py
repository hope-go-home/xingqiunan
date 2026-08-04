# 文件响应体：上传后的返回信息

from pydantic import BaseModel
from datetime import datetime


class FileResponse(BaseModel):
    """文件上传成功的返回结构"""
    id: int
    filename: str
    file_path: str
    file_size: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
