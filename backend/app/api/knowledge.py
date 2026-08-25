# 知识库路由：上传文档到知识库、搜索、查看列表、删除

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.knowledge_service import KnowledgeService, extract_text

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 上传文件大小限制（知识库文档）
MAX_KNOWLEDGE_FILE_SIZE = 20 * 1024 * 1024  # 20MB


class AddTextRequest(BaseModel):
    text: str


@router.post("/add")
async def add_document(
    req: AddTextRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """添加文本到知识库（JSON body，避免长文本超出 URL 长度限制）"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    service = KnowledgeService(db, user_id)
    doc_ids = await service.add_document(req.text)
    return {"doc_id": doc_ids[0], "chunks": len(doc_ids), "message": "添加成功"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传本地文件到知识库（自动提取文本，支持 txt/md/pdf/docx/json/csv/html 等）"""
    # 1. 读取文件内容（限制大小）
    content = await file.read()
    if len(content) > MAX_KNOWLEDGE_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 20MB 限制")

    # 2. 提取文本
    try:
        text = extract_text(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. 去掉空文本
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 4. 添加到知识库
    service = KnowledgeService(db, user_id)
    doc_ids = await service.add_document(text, metadata={"filename": file.filename or ""})
    return {"doc_ids": doc_ids, "filename": file.filename, "message": "上传成功"}


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., description="搜索关键词"),
    top_k: int = Query(5, description="返回结果数"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """语义搜索知识库"""
    service = KnowledgeService(db, user_id)
    results = await service.search(query, top_k)
    return {"results": results}


@router.get("/list")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """查看知识库所有文档"""
    service = KnowledgeService(db, user_id)
    docs = await service.list_documents()
    return {"documents": docs}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除知识库中的文档（整篇所有分块）"""
    service = KnowledgeService(db, user_id)
    await service.delete_document(doc_id)
    return {"message": "删除成功"}


class BatchDeleteRequest(BaseModel):
    ids: list[str]


@router.post("/batch_delete")
async def batch_delete_documents(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """批量删除多篇文档"""
    if not req.ids:
        raise HTTPException(status_code=400, detail="未选择要删除的文档")
    service = KnowledgeService(db, user_id)
    for gid in req.ids:
        await service.delete_document(gid)
    return {"deleted": len(req.ids), "message": f"已删除 {len(req.ids)} 篇文档"}
