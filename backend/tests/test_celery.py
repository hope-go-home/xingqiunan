# Celery 任务注册回归测试：worker 启动时若未加载任务模块（缺 include），
# 队列消息将无人消费，任务永远 pending。此测试防止该问题再次出现。

from app.tasks.celery_app import celery_app
from app.tasks.file_tasks import execute_task


def test_execute_task_registered_in_celery():
    """execute_task 必须出现在 Celery 任务注册表中"""
    assert execute_task.name in celery_app.tasks


def test_execute_task_signature():
    """任务携带可序列化参数（task_id 必须为 int）"""
    assert execute_task.name == "app.tasks.file_tasks.execute_task"
    sig = execute_task.signature(kwargs={"task_id": 1, "title": "t", "task_type": "data_calc"})
    assert sig.kwargs["task_id"] == 1