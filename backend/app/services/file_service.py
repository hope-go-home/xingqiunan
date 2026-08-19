# 文件上传业务逻辑：保存文件到磁盘（按用户分目录）并记录到数据库
# 安全：类型白名单 + 大小限制 + 流式写入（不整文件载入内存）

import aiofiles
import os
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file_record import FileRecord
from app.core.config import UPLOAD_DIR

# 上传限制
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTS = {
    ".txt", ".md", ".pdf", ".docx", ".json", ".csv", ".xml", ".html",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
    ".mp3", ".wav", ".m4a", ".ogg",
}


class FileService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def upload(self, filename: str, file: UploadFile) -> FileRecord:
        # 1. 类型白名单校验
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext or '未知'}")

        # 2. 生成唯一文件名，按用户分目录存储（工具沙箱与之一致）
        saved_name = f"{uuid.uuid4().hex}{ext}"
        user_dir = os.path.join(UPLOAD_DIR, f"user_{self.user_id}")
        os.makedirs(user_dir, exist_ok=True)
        saved_path = os.path.join(user_dir, saved_name)

        # 3. 分块流式写入，边写边校验大小，超限立即清理并报 413
        size = 0
        try:
            async with aiofiles.open(saved_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_SIZE:
                        raise HTTPException(status_code=413, detail="文件超过 20MB 限制")
                    await f.write(chunk)
        except HTTPException:
            if os.path.exists(saved_path):
                os.remove(saved_path)
            raise

        # 4. 记录到数据库
        record = FileRecord(
            filename=filename,
            file_path=saved_path,
            file_size=size,
            user_id=self.user_id,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record
