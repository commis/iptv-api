from typing import Optional, Dict, List
from urllib.parse import unquote

from fastapi import APIRouter, Query, BackgroundTasks
from starlette import status

from api.site.collector import VideoCollector
from core.logger_factory import LoggerFactory
from models.api_request import UpdateVodRequest
from models.api_response import TaskResponse
from services import config_manager, task_manager
from utils.handler import handle_exception

router = APIRouter(prefix="/site", tags=["点播接口"])
logger = LoggerFactory.get_logger(__name__)

collector = VideoCollector()


def paginate_list(data_list: List[Dict], page: int, page_size: int = 20) -> Dict:
    total = len(data_list)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = data_list[start:end]
    return {
        "list": page_data,
        "total": total,
        "page": page
    }


def get_video_detail_from_redis(sp: str, cat_name: str, video_name: str) -> Dict | None:
    define_id = f"{cat_name}/{video_name}"
    redis_key = f"tv-vod:{sp}:{cat_name}:{video_name}"
    redis_data = VideoCollector.redis_get(redis_key)
    if redis_data:
        video_data = {"vod_id": define_id, **redis_data}
        return video_data

    site_config = config_manager.get_vod_config(sp)
    return {
        "vod_id": f"{define_id}",
        "vod_name": video_name,
        "vod_pic": site_config.site_video_cover,
        "type_name": cat_name,
        "vod_remarks": "未采集",
    }


def get_video_base_from_redis(sp: str, cat_name: str, video_name: str) -> Dict | None:
    define_id = f"{cat_name}/{video_name}"
    redis_key = f"tv-vod:{sp}:{cat_name}:{video_name}"
    redis_data = VideoCollector.redis_get(redis_key)
    if redis_data:
        field_result = VideoCollector.filter_base_fields(redis_data)
        video_data = {"vod_id": define_id, **field_result}
        return video_data

    site_config = config_manager.get_vod_config(sp)
    return {
        "vod_id": f"{define_id}",
        "vod_name": video_name,
        "vod_pic": site_config.site_video_cover,
        "type_name": cat_name,
        "vod_remarks": "未采集",
    }


def get_class_data(sp: str, site_config, pg, t: str = 1) -> Dict:
    cat_name = site_config.get_site_cate_name(t)
    videos = site_config.site_videos.get(cat_name, [])
    data = [get_video_base_from_redis(sp, cat_name, name) for name in videos]
    return paginate_list(data, pg)


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
    site_config = config_manager.get_vod_config(sp)
    if not site_config:
        logger.error(f"vod: sp={sp}对应的站点配置不存在")
        return {"class": [], "list": [], "total": 0, "page": pg}

    # 视频搜索
    if wd:
        res = [
            get_video_base_from_redis(sp, cat, name)
            for cat, videos in site_config.site_videos.items()
            for name in videos
            if wd in name
        ]
        return paginate_list(res, pg)

    if ac == "detail":
        # 分类列表
        if t:
            return get_class_data(sp, site_config, pg, t)

        # 视频详情
        if ids:
            try:
                cat_name, video_name = unquote(ids).split("/", 1)
                cache = get_video_detail_from_redis(sp, cat_name, video_name)
                return {"list": [cache] if cache else []}
            except ValueError:
                logger.error(f"ids格式错误: {ids}，正确格式为 分类/文件名")
                return {"list": []}

    # 默认返回分类+空列表
    return {"class": site_config.site_class, "list": [], "total": 0, "page": 1}


@router.post("/collect", summary="全量采集", response_model=TaskResponse)
async def collect_all(request: UpdateVodRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    try:
        if not request.sp:
            handle_exception(f"sp参数不能为空", status.HTTP_400_BAD_REQUEST)

        site_config = config_manager.get_vod_config(request.sp)
        if not site_config:
            handle_exception(f"sp={request.sp}对应的站点配置不存在", status.HTTP_400_BAD_REQUEST)

        task_manager.clear()
        task_id = task_manager.create_task(
            url=f"sp={request.sp}",
            total=site_config.video_total,
            type="update_vod_video",
            description=f"update video mode: {request.is_full}",
        )

        async def run_update_vod_task() -> None:
            try:
                task = task_manager.get_task(task_id)
                result = await collector.collect_all_videos(task, request.sp, request.is_full)
                task.update({"status": "completed", "result": result})
            except Exception as re:
                logger.error(f"update vod video task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_update_vod_task)
        return TaskResponse(data={"task_id": task_id})

    except Exception as e:
        logger.error(f"update vod video request failed: {str(e)}", exc_info=True)
        handle_exception("update vod video request failed")
