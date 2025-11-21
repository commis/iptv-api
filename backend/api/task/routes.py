from typing import Dict

from fastapi import APIRouter, Path, status

from services.task import task_manager
from utils.handler import handle_exception

router = APIRouter(prefix="/task", tags=["任务管理器"])


@router.get("/list", summary="获取所有任务列表")
def get_tasks():
    """获取系统中所有任务的列表"""
    try:
        return task_manager.get_tasks()
    except Exception as e:
        handle_exception(f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}", summary="获取单个任务详情")
def get_task(task_id: str = Path(..., min_length=1, description="任务ID")):
    """根据任务ID获取任务详情"""
    task = task_manager.get_task(task_id)
    if not task:
        handle_exception(f"task id {task_id} not found", status.HTTP_404_NOT_FOUND)
    return task


@router.delete("/{task_id}", summary="删除指定任务", response_model=Dict[str, str])
def delete_task(task_id: str = Path(..., min_length=1, description="任务ID")):
    """根据任务ID删除任务"""
    result = task_manager.delete_task(task_id)
    if not result:
        handle_exception(f"任务ID {task_id} 不存在", status.HTTP_404_NOT_FOUND)

    return {"message": f"task id {task_id} deleted"}
