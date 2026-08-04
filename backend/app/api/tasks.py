# 任务路由：创建任务、查询任务列表、查看单个任务

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.task import TaskCreateRequest, TaskResponse
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["任务"])


@router.post("/", response_model=TaskResponse)
async def create_task(
    req: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """创建任务，需登录"""
    service = TaskService(db, user_id)
    return await service.create(req)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取当前用户的所有任务（按创建时间倒序）"""
    service = TaskService(db, user_id)
    return await service.list_tasks()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """查看单个任务详情"""
    service = TaskService(db, user_id)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
