from typing import Dict

from pydantic import BaseModel


class TaskResponse(BaseModel):
    code: int = 202
    message: str = "任务已接受"
    data: Dict[str, str]


class MiguResponse(BaseModel):
    code: int = 200
    url: str
    message: str = "成功生成播放地址"
    data: Dict[str, str]
