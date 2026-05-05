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

    # 只返回 TVBox 需要的 3 个字段！
    return {
        "list": page_data,
        "total": total,
        "page": page
    }


def get_video_from_redis(cat_name: str, video_name: str) -> Dict | None:
    redis_key = f"tv-vod:{cat_name}:{video_name}"
    redis_data = VideoCollector.redis_get(redis_key)
    if redis_data:
        return redis_data

    site_config = config_manager.video_vod_config
    return {
        "vod_id": f"{cat_name}/{video_name}",
        "vod_name": video_name,
        "vod_pic": site_config.site_video_cover,
        "type_name": cat_name,
        "vod_remarks": "未采集",
    }


@router.get("/edu/vod", summary="查询点播数据")
async def get_vod(
    ac: Optional[str] = Query(None, description="操作名称，例如：[list | detail]"),
    t: Optional[str] = Query(None, description="分类ID，例如：1"),
    ids: Optional[str] = Query(None, description="详情ID (格式: 分类/文件名)"),
    wd: Optional[str] = Query(None, description="搜索关键词"),
    pg: int = Query(1, description="分页，默认值：1")  #
):
    logger.debug(f"edu vod: ac={ac}, t={t}, ids={ids}, wd={wd}, pg={pg}")
    site_config = config_manager.video_vod_config
    site_class = site_config.site_class
    site_videos = site_config.site_videos

    # 搜索
    if wd:
        res = []
        for cat, videos in site_videos.items():
            for name in videos:
                if wd in name:
                    res.append(get_video_from_redis(cat, name))
        page_result = paginate_list(res, pg)
        return {"class": site_class, **page_result}

    # 详情
    if ac == "detail" and ids:
        try:
            vod_id = unquote(ids)
            cat_name, video_name = vod_id.split("/", 1)
        except:
            return {"list": []}

        cache = get_video_from_redis(cat_name, video_name)
        return cache if cache else {"list": []}

    # 分类列表
    if t:
        cat_name = site_config.get_site_cate_name(t)
        videos = site_videos.get(cat_name, [])
        data = [get_video_from_redis(cat_name, name) for name in videos]
        page_result = paginate_list(data, pg)
        return {"class": site_class, **page_result}

    # 兜底的默认数据
    return {"class": site_class, "list": [], "total": 0, "page": 1}


@router.post("/collect/all", summary="全量采集", response_model=TaskResponse)
async def collect_all(request: UpdateVodRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    try:
        task_manager.clear()
        site_config = config_manager.video_vod_config
        task_id = task_manager.create_task(
            url="",
            total=site_config.video_total,
            type="update_vod_video",
            description=f"update video mode: {request.is_full}",
        )

        async def run_update_vod_task() -> None:
            try:
                task = task_manager.get_task(task_id)
                result = await collector.collect_all_videos(task, is_full=request.is_full)
                task.update({"status": "completed", "result": result})
            except Exception as re:
                logger.error(f"update vod video task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_update_vod_task)
        return TaskResponse(data={"task_id": task_id})

    except ValueError as ve:
        handle_exception(str(ve), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"update vod video request failed: {str(e)}", exc_info=True)
        handle_exception("update vod video request failed")
