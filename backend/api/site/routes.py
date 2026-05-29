import re
from typing import Optional
from urllib.parse import quote, unquote

import httpx
import starlette
from fastapi import APIRouter, Query, Request, BackgroundTasks, Path
from starlette import status
from starlette.responses import RedirectResponse, StreamingResponse

from core.logger_factory import LoggerFactory
from models.api_request import UpdateVodRequest
from models.api_response import TaskResponse, ApiResponse
from services import task_manager, config_manager
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


@router.get("/player/{sp}/{id}", summary="解析视频播放地址")
async def parse_channel_url(
        sp: str = Path(..., description="视频源，如 v-youtub"),
        id: str = Path(..., description="频道ID，例如：4fkoZ7z5ggM"),
        tp: Optional[str] = Query(None, description="返回的数据类型，例如：json")
):
    logger.debug(f"player: sp={sp}, id={id}")
    resp_data = {"op": "player", "sp": sp, "id": id, "type": tp}
    resp_message = "失败解析播放地址"

    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"player: sp={sp}对应的站点配置不存在")
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
        logger.error(f"player {sp}.{id} video failed: {str(e)}", exc_info=False)
    return ApiResponse(code=101, message=resp_message, data=resp_data)


@router.get("/m3u8/{sp}/{id}", summary="视频播放 seg_ts 地址")
async def get_ts_url(
        sp: str = Path(..., description="视频源，如 v-youtub"),
        id: str = Path(..., description="频道ID，例如：4fkoZ7z5ggM")
):
    logger.debug(f"m3u8: sp={sp}, id={id}")
    resp_data = {"op": "m3u8", "sp": sp, "id": id}
    resp_message = "失败m3u8播放地址"

    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"m3u8: sp={sp}对应的站点配置不存在")
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
            player_url = real_player.pop("url")
            json_data = spider.get_player_json(1, id, player_url)
            async with (httpx.AsyncClient(timeout=20) as client):
                resp = await client.get(player_url, headers=json_data["header"])
                resp.raise_for_status()
                raw_m3u8 = resp.text

                base_url = config_manager.service_params.url_parse.split('/m3u8')[0]

                def replace_ts_url(match):
                    original_url = match.group(0)
                    proxy_url = f"{base_url}/proxy/{sp}?url={quote(original_url, safe='')}"
                    return proxy_url

                modified_m3u8 = re.sub(r'https?://[^\s#]+?/seg\.ts[^\s#]*', replace_ts_url, raw_m3u8)
                return starlette.responses.Response(
                    content=modified_m3u8,
                    media_type="application/vnd.apple.mpegurl"
                )
    except Exception as e:
        logger.error(f"m3u8 {sp}.{id} video failed.", exc_info=False)
    return ApiResponse(code=101, message=resp_message, data=resp_data)


@router.get("/proxy/{sp}", summary="代理视频流播放")
async def proxy_ts_url(
        request: Request,
        sp: str = Path(..., description="视频源，如 v-youtub"),
        url: str = Query(..., description="播放 ts 地址")
):
    logger.debug(f"proxy: sp={sp}, url={url}")
    resp_data = {"op": "set_ts", "sp": sp}
    resp_message = "失败代理视频流播放"

    spider = SpiderFactory.get_spider(sp)
    if not spider or not spider.config:
        logger.error(f"proxy: sp={sp}对应的站点配置不存在")
        return ApiResponse(code=400, message=resp_message, data=resp_data)

    player_url = unquote(url)
    headers = spider.get_player_json(1, -1, "").pop("header")
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header
    logger.debug(f"proxy {sp} request header: {headers}")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
            resp = await client.get(player_url)
            resp.raise_for_status()
            resp_headers = {
                "Content-Type": "video/mp2t",
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
            }
            for k in ["content-length", "content-range", "cache-control"]:
                if k in resp.headers:
                    resp_headers[k.capitalize()] = resp.headers[k]
            logger.debug(f"proxy {sp} resp_header: {resp_headers}")
            return StreamingResponse(
                resp.aiter_bytes(),
                status_code=resp.status_code,
                headers=resp_headers
            )
    except Exception as e:
        logger.error(f"proxy {sp} video failed: {str(e)}", exc_info=False)

    async def generate_empty_bytes():
        yield b""

    return StreamingResponse(generate_empty_bytes(), status_code=500, media_type="video/mp2t")
