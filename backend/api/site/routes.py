from typing import Optional, Dict
from urllib.parse import unquote

from fastapi import APIRouter, Query

from api.site.collector import VideoCollector
from core.logger_factory import LoggerFactory
from services import config_manager

router = APIRouter(prefix="/site", tags=["点播接口"])
logger = LoggerFactory.get_logger(__name__)

collector = VideoCollector()


def get_video_from_redis(cat_name: str, video_name: str) -> Dict | None:
    redis_key = f"tv-vod:{cat_name}:{video_name}"
    redis_data = VideoCollector.redis_get(redis_key)
    if redis_data:
        return redis_data

    return {
        "vod_id": f"{cat_name}/{video_name}",
        "vod_name": video_name,
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
    logger.info(f"edu vod: ac={ac}, t={t}, ids={ids}, wd={wd}, pg={pg}")
    site_class = config_manager.site_class
    site_videos = config_manager.site_videos

    # 搜索
    if wd:
        res = []
        for cat, videos in site_videos.items():
            for name in videos:
                if wd in name:
                    res.append(get_video_from_redis(cat, name))
        return {"class": site_class, "list": res, "total": len(res), "page": pg}

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
        cat_name = config_manager.get_site_cate_name(t)
        videos = site_videos.get(cat_name, [])
        data = [get_video_from_redis(cat_name, name) for name in videos]
        return {"class": site_class, "list": data, "total": len(data), "page": pg}

    # 默认
    return {"class": site_class, "list": [], "total": 0, "page": 1}


@router.post("/collect/all", summary="全量采集")
async def collect_all(
    update: bool = Query(False, description="True=强制更新所有缓存")
):
    result = await collector.collect_all_videos(update=update)
    return {"msg": "采集完成", **result}
