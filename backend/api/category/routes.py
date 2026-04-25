from typing import Dict, List

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from starlette import status

from services import config_manager
from utils.handler import handle_exception

router = APIRouter(prefix="/category", tags=["分类管理接口"])


class UpdateCategoryRequest(BaseModel):
    """更新直播源请求"""
    name: str = Field(..., description="分类名称")
    icon: str = Field(..., description="分类图标")
    channels: List[str] = Field(default=[], description="包含频道列表")
    excludes: List[str] = Field(default=[], description="排除频道列表")


@router.get("/list", summary="获取所有分类", response_model=Dict[str, object])
def get_all_category_icons():
    """获取所有分类及其对应的图标"""
    return config_manager.list_categories()


@router.post("/data", summary="添加/更新分类", response_model=Dict[str, object])
def update_category_data(
    request: UpdateCategoryRequest = Body(..., media_type="application/json", description="更新分类数据")):
    """
    添加或更新分类图标
    """
    if not request:
        handle_exception("icon data is empty", status.HTTP_400_BAD_REQUEST)

    try:
        config_manager.update_category({request.name: request.model_dump()})
        return config_manager.list_categories()
    except Exception as e:
        handle_exception(str(e))


@router.get("/{category_name}", summary="获取单个分类", response_model=Dict[str, object])
def get_category_info(category_name: str):
    """获取指定分类的图标"""
    category_info = config_manager.get_category_info(category_name)
    if category_info is None:
        handle_exception(f"category '{category_name}' not found", status.HTTP_404_NOT_FOUND)
    return category_info


@router.delete("/{category_name}", summary="删除分类", response_model=Dict[str, object])
def delete_category_icon(category_name: str):
    """
    删除指定分类的图标
    """
    if not config_manager.exists(category_name):
        raise HTTPException(status_code=404, detail=f"分类 '{category_name}' 不存在")

    config_manager.remove_category(category_name)
    return config_manager.list_categories()
