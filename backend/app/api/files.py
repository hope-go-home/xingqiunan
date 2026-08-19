# 文件路由：/files/upload 上传文件

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.file import FileResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件"])


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传文件，需登录（请求头带 Authorization: Bearer <token>）。大小/类型限制见 FileService"""
    service = FileService(db, user_id)
    return await service.upload(file.filename, file)
