from typing import Optional

import httpx
from fastapi import APIRouter, Query, BackgroundTasks, Path
from httpx import ReadError, RemoteProtocolError
from starlette import status
from starlette.responses import RedirectResponse, StreamingResponse

from core.logger_factory import LoggerFactory
from models.api_request import UpdateVodRequest
from models.api_response import TaskResponse, ApiResponse
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
        return await spider.search_data(wd, pg)

    # 详情数据
    if ac == "detail":
        if ids:
            return await spider.get_detail_data(ids)
        if t:
            return await spider.get_list_data(t, pg)

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


@router.get("/{sp}/{id}", summary="解析视频播放地址")
async def parse_channel_url(
        sp: str = Path(..., description="视频源，如 v-youtub"),
        id: str = Path(..., description="频道ID，例如：4fkoZ7z5ggM"),
        tp: Optional[str] = Query(None, description="返回的数据类型，例如：json")
):
    logger.debug(f"parse: sp={sp}, id={id}")
    resp_data = {"op": "parse", "sp": sp, "id": id, "type": tp}
    resp_message = "失败解析播放地址"

    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"vod: sp={sp}对应的站点配置不存在")
        return ApiResponse(code=400, message=resp_message, data=resp_data)

    try:
        redis_key = spider.make_redis_key("player", id)
        real_player = spider.redis_get(redis_key)
        if not real_player:
            player_url = await spider.get_player(id)
            if player_url:
                real_player = {"url": player_url}
                spider.redis_set(redis_key, real_player, ex=-1)

        if real_player:
            json_data = spider.get_player_json(1, id, real_player["url"])
            player_url = json_data.pop("url")
            match tp:
                case "json":
                    return ApiResponse(url=player_url, data=json_data)
                case _:
                    logger.debug(f"parse {id} play url: {player_url}")
                    return RedirectResponse(
                        url=player_url, status_code=302,
                        headers=json_data["header"]
                    )
    except Exception as e:
        logger.error(f"parse {id} video failed.", exc_info=False)
    return ApiResponse(code=101, message=resp_message, data=resp_data)


@router.get("/proxy/{sp}/{id}", summary="代理视频播放地址")
async def proxy_channel_url(
        sp: str = Path(..., description="视频源，如 v-youtub"),
        id: str = Path(..., description="频道ID，例如：4fkoZ7z5ggM")
):
    logger.debug(f"proxy: sp={sp}, vid={id}")
    resp_data = {"op": "proxy", "sp": sp, "id": id}
    resp_message = "失败代理播放地址"

    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"vod: sp={sp}对应的站点配置不存在")
        return ApiResponse(code=400, message=resp_message, data=resp_data)

    try:
        redis_key = spider.make_redis_key("player", id)
        real_player = spider.redis_get(redis_key)
        if not real_player:
            player_url = await spider.get_player(id)
            if player_url:
                real_player = {"url": player_url}
                spider.redis_set(redis_key, real_player, ex=-1)

        if real_player:
            json_data = spider.get_player_json(1, id, real_player["url"])
            player_url = json_data.pop("url")
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.send(
                    client.build_request("GET", player_url, headers=json_data["header"]),
                    stream=True)
                resp_headers = {
                    "Content-Type": resp.headers.get("content-type", "video/mp4"),
                    "Accept-Ranges": "bytes",
                }
                cl = resp.headers.get("content-length")
                if cl and cl.isdigit():
                    resp_headers["Content-Length"] = cl

                async def safe_stream():
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    except (ReadError, RemoteProtocolError) as e:
                        # logger.warning(f"Stream interrupted for {id}: {e}")
                        pass

                return StreamingResponse(
                    safe_stream(),
                    status_code=resp.status_code,
                    headers=resp_headers,
                )
    except Exception as e:
        logger.error(f"proxy {id} video failed.", exc_info=False)
    return ApiResponse(code=101, message=resp_message, data=resp_data)
