# 文件上传业务逻辑：保存文件到磁盘并记录到数据库

import aiofiles
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file_record import FileRecord
from app.core.config import UPLOAD_DIR


class FileService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def upload(self, filename: str, content: bytes) -> FileRecord:
        # 1. 生成唯一文件名（UUID），防止重名覆盖
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        saved_name = f"{uuid.uuid4().hex}.{ext}"
        saved_path = os.path.join(UPLOAD_DIR, saved_name)

        # 2. 创建目录（如果不存在）并写入文件
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        async with aiofiles.open(saved_path, "wb") as f:
            await f.write(content)

        # 3. 记录到数据库
        record = FileRecord(
            filename=filename,
            file_path=saved_path,
            file_size=len(content),
            user_id=self.user_id,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record
