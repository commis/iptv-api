from typing import Optional

from fastapi import APIRouter, Query, BackgroundTasks
from starlette import status

from core.logger_factory import LoggerFactory
from models.api_request import UpdateVodRequest
from models.api_response import TaskResponse
from services import task_manager
from services.spider.factory import SpiderFactory
from utils.handler import handle_exception

router = APIRouter(prefix="/site", tags=["点播接口"])
logger = LoggerFactory.get_logger(__name__)


@router.get("/vod", summary="查询点播数据")
async def get_vod(
        sp: Optional[str] = Query("v-docs", description="来源标识，如 v-docs"),
        ac: Optional[str] = Query(None, description="操作名称，例如：[list | detail]"),
        t: Optional[str] = Query(None, description="分类ID，例如：1"),
        ids: Optional[str] = Query(None, description="详情ID (格式: 分类/文件名)"),
        wd: Optional[str] = Query(None, description="搜索关键词"),
        pg: int = Query(1, description="分页，默认值：1")  #
):
    logger.debug(f"vod: sp={sp}, ac={ac}, t={t}, ids={ids}, wd={wd}, pg={pg}")
    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"vod: sp={sp}对应的站点配置不存在")
        return {"class": [], "list": [], "total": 0, "page": pg}

    # 搜索优先
    if wd:
        return spider.search_data(wd, pg)

    # 详情数据
    if ac == "detail":
        if ids:
            return spider.get_detail_data(ids)
        if t:
            return spider.get_list_data(t, pg)

    # 默认返回分类（ac=list）
    return {"class": spider.config.site_class, "list": []}


@router.post("/collect", summary="数据采集", response_model=TaskResponse)
async def api_collect(request: UpdateVodRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    try:
        spider = SpiderFactory.get_spider(request.sp)
        if not spider or not spider.config:
            handle_exception(f"sp={request.sp}对应的站点配置不存在", status.HTTP_400_BAD_REQUEST)

        task_manager.clear()
        task_id = task_manager.create_task(
            url=f"sp={request.sp}",
            total=spider.config.video_total,
            type="update_vod_video",
            description=f"update video mode: {request.is_full}",
        )

        async def run_task():
            task_info = task_manager.get_task(task_id)
            result = await spider.collect(task_info, request.is_full)
            task_info.update({"status": "completed", "result": result})

        background_tasks.add_task(run_task)
        return TaskResponse(data={"task_id": task_id})
    except Exception as e:
        logger.error(f"update vod video request failed: {str(e)}", exc_info=True)
        handle_exception(f"update vod video request failed.")
