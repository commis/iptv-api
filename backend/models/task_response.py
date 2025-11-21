from typing import Dict

from pydantic import BaseModel


class TaskResponse(BaseModel):
    """任务响应模型"""
    code: int = 202
    message: str = "任务已接受"
    data: Dict[str, str]