# 文件路由：/files/upload 上传文件

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.file import FileResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件"])

# 上传限制
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".log",
    ".pdf", ".docx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
    ".wav", ".mp3", ".m4a", ".ogg", ".flac",
}
ALLOWED_MIMES = {
    "text/plain", "text/markdown", "application/json", "text/csv",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp",
    "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/flac",
    "application/octet-stream",
}


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传文件，需登录，限制 50MB + 白名单扩展名"""
    # 扩展名校验
    ext = ("." + file.filename.rsplit(".", 1)[-1].lower()) if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # MIME 校验
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    # 流式读取 + 大小限制
    chunks = []
    total = 0
    while chunk := await file.read(8192):
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"文件过大，最大 {MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    service = FileService(db, user_id)
    return await service.upload(file.filename, content)
