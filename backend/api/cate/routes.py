from typing import Dict

from fastapi import APIRouter
from starlette import status

from services import config_manager
from utils.handler import handle_exception

router = APIRouter(prefix="/category", tags=["分类管理接口"])


@router.get("/list", summary="获取所有分类", response_model=Dict[str, object])
def get_all_category_icons():
    """获取所有分类及其对应的图标"""
    return config_manager.list_categories()


@router.get("/{category_name}", summary="获取单个分类", response_model=Dict[str, object])
def get_category_info(category_name: str):
    """获取指定分类的图标"""
    category_info = config_manager.get_category_info(category_name)
    if category_info is None:
        handle_exception(f"category '{category_name}' not found", status.HTTP_404_NOT_FOUND)
    return category_info
