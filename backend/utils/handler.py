from typing import NoReturn

from fastapi import HTTPException
from starlette import status


def handle_exception(error_msg: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> NoReturn:
    """统一异常处理函数"""
    raise HTTPException(status_code=status_code, detail=error_msg)
