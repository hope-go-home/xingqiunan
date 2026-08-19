"""
任务业务逻辑：创建、查询任务列表、获取单个任务。
创建任务时自动提交到 Celery 异步队列执行。
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.schemas.task import TaskCreateRequest, TaskResponse

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def create(self, req: TaskCreateRequest) -> TaskResponse:
        """创建任务并提交到 Celery 异步执行"""
        task = Task(
            title=req.title,
            description=req.description,
            task_type=req.task_type,
            user_id=self.user_id,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # 提交到 Celery 异步队列执行（失败不影响创建结果，记日志便于排查）
        try:
            from app.tasks.file_tasks import execute_task
            execute_task.delay(
                task_id=task.id,
                title=task.title,
                task_type=task.task_type,
                description=task.description or "",
            )
        except Exception as e:
            logger.warning("任务 %s 提交 Celery 队列失败（保持 pending）: %s", task.id, e)

        return TaskResponse.model_validate(task)

    async def list_tasks(self) -> list[TaskResponse]:
        """查询当前用户的所有任务（按创建时间倒序）"""
        result = await self.db.execute(
            select(Task).where(Task.user_id == self.user_id).order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        return [TaskResponse.model_validate(t) for t in tasks]

    async def get_task(self, task_id: int) -> TaskResponse | None:
        """查询单个任务（只返回当前用户的）"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == self.user_id)
        )
        task = result.scalar_one_or_none()
        return TaskResponse.model_validate(task) if task else None
