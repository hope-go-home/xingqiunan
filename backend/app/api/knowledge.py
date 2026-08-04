# 知识库路由：上传文档到知识库、搜索、查看列表、删除

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.post("/add")
async def add_document(
    text: str = Query(..., description="文档内容"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """添加文本到知识库"""
    service = KnowledgeService(db, user_id)
    doc_id = await service.add_document(text)
    return {"doc_id": doc_id, "message": "添加成功"}


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
    """删除知识库中的文档"""
    service = KnowledgeService(db, user_id)
    await service.delete_document(doc_id)
    return {"message": "删除成功"}
