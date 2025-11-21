from typing import Dict, List

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from starlette import status

from services.category import category_manager
from utils.handler import handle_exception

router = APIRouter(prefix="/category", tags=["分类图标管理"])


class UpdateCategoryRequest(BaseModel):
    """更新直播源请求"""
    name: str = Field(..., description="分类名称")
    icon: str = Field(..., description="分类图标")
    channels: List[str] = Field(default=[], description="包含频道列表")
    excludes: List[str] = Field(default=[], description="排除频道列表")


@router.get("/icons", summary="获取所有分类图标", response_model=Dict[str, object])
def get_all_category_icons():
    """获取所有分类及其对应的图标"""
    return category_manager.list_categories()


@router.get("/icons/{category_name}", summary="获取单个分类图标", response_model=Dict[str, object])
def get_category_info(category_name: str):
    """获取指定分类的图标"""
    category_info = category_manager.get_category_info(category_name)
    if category_info is None:
        handle_exception(f"category '{category_name}' not found", status.HTTP_404_NOT_FOUND)
    return category_info


@router.post("/icons", summary="添加/更新分类图标", response_model=Dict[str, object])
def update_category_data(
        request: UpdateCategoryRequest = Body(..., media_type="application/json", description="更新分类数据")):
    """
    添加或更新分类图标
    """
    if not request:
        handle_exception("icon data is empty", status.HTTP_400_BAD_REQUEST)

    try:
        category_manager.update_category({request.name: request.model_dump()})
        return category_manager.list_categories()
    except Exception as e:
        handle_exception(str(e))


@router.delete("/icons/{category_name}", summary="删除分类图标", response_model=Dict[str, object])
def delete_category_icon(category_name: str):
    """
    删除指定分类的图标
    """
    if not category_manager.exists(category_name):
        raise HTTPException(status_code=404, detail=f"分类 '{category_name}' 不存在")

    category_manager.remove_category(category_name)
    return category_manager.list_categories()
