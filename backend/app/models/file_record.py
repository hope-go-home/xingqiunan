# 文件记录模型：对应数据库 files 表，记录每次上传的文件信息

from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from datetime import datetime
from app.core.database import Base


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)        # 主键
    filename = Column(String(256), nullable=False)                    # 原始文件名
    file_path = Column(String(512), nullable=False)                   # 服务器上的存储路径
    file_size = Column(BigInteger, default=0)                         # 文件大小（字节）
    status = Column(String(32), default="uploaded")                   # 状态：uploaded / processing / done
    user_id = Column(Integer, nullable=False)                         # 上传者 ID
    created_at = Column(DateTime, default=datetime.utcnow)            # 上传时间
