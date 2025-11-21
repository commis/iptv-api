import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Body, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator, field_validator
from starlette import status

from api.tv.converter import LiveConverter
from api.tv.merger import LiveMerger
from core.logger_factory import LoggerFactory
from models.channel_info import ChannelInfo, ChannelUrl
from models.task_response import TaskResponse
from services.channel import channel_manager
from services.checker import ChannelChecker
from services.task import task_manager
from utils.handler import handle_exception
from utils.parser import Parser

router = APIRouter(prefix="/tv", tags=["M3U工具"])
logger = LoggerFactory.get_logger(__name__)


class SingleCheckRequest(BaseModel):
    """单个频道检查请求模型"""
    url: str = Field(..., description="频道URL")
    rule: str = Field(default="/{i}/", description="解析规则，必须包含{i}占位符")

    @field_validator('url')
    def valid_url(cls, value):
        """验证URL格式是否有效"""
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                raise ValueError("无效的URL格式")
            return value
        except ValueError as e:
            raise ValueError(f"URL验证失败: {str(e)}")

    @field_validator('rule')
    def rule_contains_placeholder(cls, value):
        """验证规则中是否包含{i}占位符"""
        if '{i}' not in value:
            raise ValueError("规则必须包含{i}占位符")
        return value

    def extract_id(self, url: str) -> str:
        """从URL中提取频道ID，若未找到则返回1"""
        pattern = re.escape(self.rule).replace('\\{i\\}', '(\\d+)')
        match = re.search(pattern, url)
        return match.group(1) if match else 'index'


class BatchCheckRequest(BaseModel):
    """批量频道检查请求模型"""
    url: str = Field(..., description="包含{i}占位符的基础URL")
    start: int = Field(1, ge=1, description="起始频道ID")
    size: int = Field(10, ge=1, le=1000, description="检查数量上限1000")
    is_clear: Optional[bool] = Field(True, description="是否清空已有频道数据")
    thread_size: Optional[int] = Field(20, ge=2, le=64, description="并发线程数上限50")


class EpgRequest(BaseModel):
    file: Optional[str] = Field(default=None, description="直播源回放信息文件")
    source: Optional[str] = Field(default=None, description="EPG源名称")
    domain: Optional[str] = Field(default=None, description="LOGO文件域名")


class UpdateLiveRequest(BaseModel):
    """更新直播源请求"""
    output: str = Field(default="/usr/share/nginx/tvbox/result.txt", description="直播源输出文件名")
    url: Optional[str] = Field(default=None, description="直播源同步URL")
    epg: Optional[EpgRequest] = Field(default=None, description="EPG源信息")
    is_clear: Optional[bool] = Field(True, description="是否清空已有频道数据")
    thread_size: Optional[int] = Field(20, ge=2, le=64, description="并发线程数上限64")
    low_limit: Optional[int] = Field(5, ge=5, le=300, description="自动更新频道数量下限")


class ChannelQuery(BaseModel):
    speed: int

    @model_validator(mode='after')
    def check_speed(cls, values):
        if not values.speed or values.speed.strip() == '':
            raise ValueError("任务ID不能为空")
        return values


@router.post("/single", summary="检查单个频道", response_class=Response)
def check_single_channel(request: SingleCheckRequest) -> Response:
    """检查单个电视频道并返回解析结果"""
    try:
        url_info = ChannelUrl(request.url)
        channel_info = ChannelInfo(request.extract_id(request.url))
        channel_info.add_url(url_info)

        checker = ChannelChecker(request.url)
        check_result = checker.check_single_with_timeout(channel_info, url_info, check_sub_m3u8=True)
        if not check_result:
            return Response(content="", media_type="text/plain")

        content = channel_info.get_all()
        return Response(content=content, media_type="text/plain")

    except ValueError as ve:
        handle_exception(str(ve))
    except Exception as e:
        logger.error(f"single check failed: {str(e)}", exc_info=True)
        handle_exception("single check failed")


@router.post("/batch", summary="批量检查频道", response_model=TaskResponse)
def check_batch_channels(request: BatchCheckRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """异步批量检查多个电视频道"""
    try:
        if request.is_clear:
            channel_manager.clear()
            task_manager.clear()

        task_id = task_manager.create_task(
            url=request.url,
            total=request.size,
            type="batch_channel_check",
            description=f"从ID {request.start} 开始检查 {request.size} 个频道"
        )

        def run_batch_check_task() -> None:
            """后台运行的批量检查任务"""
            try:
                task_manager.update_task(task_id, status="running")
                task = task_manager.get_task(task_id)

                checker = ChannelChecker(request.url, request.start, request.size)
                success_count = checker.check_batch(threads=request.thread_size, task_status=task, check_sub_m3u8=True)

                success_ids = channel_manager.channel_ids()
                task.update({
                    "status": "completed",
                    "result": {"success": success_count, "channels": success_ids}
                })
            except Exception as re:
                logger.error(f"batch check failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_batch_check_task)
        return TaskResponse(data={"task_id": task_id})
    except ValueError as ve:
        handle_exception(str(ve))
    except Exception as e:
        logger.error(f"batch check failed: {str(e)}", exc_info=True)
        handle_exception("batch check failed")


@router.post("/update/txt", summary="自动从txt更新直播源", response_model=TaskResponse)
def update_txt_sources(request: UpdateLiveRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """
    自动更新直播源数据
    """
    try:
        if request.is_clear:
            channel_manager.clear()
            task_manager.clear()

        # 填充默认值
        if request.url is None:
            request.url = "https://gh-proxy.com/github.com/vbskycn/iptv/blob/master/tv/iptv4.txt"
        if request.epg is None:
            request.epg = EpgRequest(
                file="http://epg.51zmt.top:8000/e.xml",
                source="?ch={name}&date={date}",
                domain=""
            )

        channel_manager.set_epg(file=request.epg.file, source=request.epg.source, domain=request.epg.domain)

        parser = Parser()
        parser.load_remote_url_txt(request.url)
        total_count = channel_manager.total_count()
        if total_count <= request.low_limit:
            channel_manager.clear()
            handle_exception(f"live sources count is too low: {total_count} (less than {request.low_limit})")

        task_id = task_manager.create_task(
            url=request.url,
            total=total_count,
            type="update_live_sources",
            description=f"output: {request.output}"
        )

        def run_update_live_task() -> None:
            """后台运行的批量检查任务"""
            try:
                task_manager.update_task(task_id, status="running")
                task = task_manager.get_task(task_id)

                checker = ChannelChecker(request.url)
                success_count = checker.update_batch_live(
                    threads=request.thread_size,
                    task_status=task,
                    check_m3u8_invalid=False,
                    output_file=request.output
                )
                task.update({
                    "status": "completed",
                    "result": {"success": success_count}
                })
            except Exception as re:
                logger.error(f"update live sources task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_update_live_task)
        return TaskResponse(data={"task_id": task_id})
    except ValueError as ve:
        handle_exception(str(ve), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"update txt live sources request failed: {str(e)}", exc_info=True)
        handle_exception("update txt live sources request failed")


@router.post("/update/m3u", summary="自动从m3u更新直播源", response_model=TaskResponse)
def update_m3u_sources(request: UpdateLiveRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """
    自动更新直播源数据
    """
    try:
        if request.is_clear:
            channel_manager.clear()
            task_manager.clear()

        # 填充默认值
        if request.url is None:
            request.url = "https://develop202.github.io/migu_video/interface.txt"
        if request.epg is None:
            request.epg = EpgRequest(
                file="https://develop202.github.io/migu_video/playback.xml",
                source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}",
                domain=""
            )

        channel_manager.set_epg(file=request.epg.file, source=request.epg.source, domain=request.epg.domain)

        parser = Parser()
        parser.load_remote_url_m3u(request.url)
        total_count = channel_manager.total_count()
        if total_count <= request.low_limit:
            channel_manager.clear()
            handle_exception(f"live sources count is too low: {total_count} (less than {request.low_limit})")

        task_id = task_manager.create_task(
            url=request.url,
            total=total_count,
            type="update_live_sources",
            description=f"output: {request.output}"
        )

        def run_update_live_task() -> None:
            """后台运行的批量检查任务"""
            try:
                task_manager.update_task(task_id, status="running")
                task = task_manager.get_task(task_id)

                checker = ChannelChecker(request.url)
                success_count = checker.update_batch_live(
                    threads=request.thread_size,
                    task_status=task,
                    check_m3u8_invalid=False,
                    output_file=request.output
                )
                task.update({
                    "status": "completed",
                    "result": {"success": success_count}
                })
            except Exception as re:
                logger.error(f"update live sources task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_update_live_task)
        return TaskResponse(data={"task_id": task_id})
    except ValueError as ve:
        handle_exception(str(ve), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"update m3u live sources request failed: {str(e)}", exc_info=True)
        handle_exception("update m3u live sources request failed")


@router.get("/show/txt", summary="获取频道列表(TXT格式)", response_class=Response)
def get_channels_txt():
    """获取所有可用频道的TXT格式列表"""
    try:
        content = channel_manager.to_txt_string()
        return Response(content=content, media_type="text/plain")
    except Exception as e:
        logger.error(f"obtain channel txt list failed: {str(e)}", exc_info=True)
        handle_exception("obtain channel txt list failed")


@router.get("/show/m3u", summary="获取频道列表(M3U格式)", response_class=Response)
def get_channels_m3u():
    """获取所有可用频道的M3U格式列表"""
    try:
        content = channel_manager.to_m3u_string()
        return Response(content=content, media_type="application/vnd.apple.mpegurl")
    except Exception as e:
        logger.error(f"obtain channel m3u list failed: {str(e)}", exc_info=True)
        handle_exception("obtain channel m3u list failed")


@router.post("/cvt/txt", summary="TXT格式转换为M3U格式", response_model=str)
def convert_txt_to_m3u(
        txt_data: str = Body(..., media_type="text/plain", min_length=1, description="待转换的TXT格式直播源数据")):
    """
    将TXT格式的直播源数据转换为M3U格式
    """
    try:
        converter = LiveConverter()
        result = converter.txt_to_m3u(txt_data)
        return Response(content=result, media_type="text/plain")
    except Exception as e:
        handle_exception(f"conversion failed: {str(e)}")


@router.post("/cvt/m3u", summary="M3U格式转换为TXT格式", response_model=str)
def convert_m3u_to_txt(
        m3u_data: str = Body(..., media_type="text/plain", min_length=1, description="待转换的M3U格式直播源数据")):
    """
    将M3U格式的直播源数据转换为TXT格式
    """
    try:
        if not m3u_data.strip():
            handle_exception("invalidate input: empty text", status.HTTP_400_BAD_REQUEST)

        converter = LiveConverter()
        result = converter.m3u_to_txt(m3u_data)
        return Response(content=result, media_type="text/plain")
    except Exception as e:
        handle_exception(f"conversion failed: {str(e)}")


@router.post("/mgr/txt", summary="合并TXT格式直播源并选择最优", response_model=str)
def merge_live_sources(
        txt_data: str = Body(..., media_type="text/plain", min_length=1, description="待合并的TXT格式直播源数据"),
        top_n: int = Query(3, ge=1, le=10, description="选择排名前N的直播源(1-10)")):
    """
    合并TXT格式的直播源数据并选择最优的前N个
    """
    try:
        if not txt_data.strip():
            handle_exception("invalidate input: empty text", status.HTTP_400_BAD_REQUEST)

        live_data = Parser.get_channel_data(txt_data)
        merger = LiveMerger(live_data)
        merger.find_top_hosts(n=top_n)
        result = merger.format_output()
        return Response(content=result, media_type="text/plain")
    except ValueError as ve:
        handle_exception(f"parse channel data failed: {str(ve)}")
    except Exception as e:
        handle_exception(f"merge live sources failed: {str(e)}")


@router.post("/chr/txt", summary="检测TXT格式直播源有效性", response_model=TaskResponse)
def check_live_sources(
        background_tasks: BackgroundTasks,
        txt_data: str = Body(..., media_type="text/plain", min_length=1, description="待合并的TXT格式直播源数据"),
        is_clear: Optional[bool] = Query(True, description="是否清空已有频道数据"),
        thread_size: Optional[int] = Query(20, ge=2, le=64, description="并发线程数上限64")):
    """
    检测TXT格式直播源有效性
    """
    try:
        if not txt_data:
            handle_exception("invalidate input: empty text", status.HTTP_400_BAD_REQUEST)

        if is_clear:
            channel_manager.clear()
            task_manager.clear()

        Parser.load_channel_txt(txt_data)
        total_count = channel_manager.total_count()
        if total_count <= 0:
            handle_exception(f"invalidate input: no valid channel data found")

        task_id = task_manager.create_task(
            url="",
            total=total_count,
            type="update_live_sources",
            description=f"检查TXT直播源有效性"
        )

        def run_check_live_task() -> None:
            """后台运行的批量检查任务"""
            try:
                task_manager.update_task(task_id, status="running")
                task = task_manager.get_task(task_id)

                checker = ChannelChecker()
                success_count = checker.update_batch_live(threads=thread_size,
                                                          task_status=task,
                                                          check_m3u8_invalid=True)
                task.update({
                    "status": "completed",
                    "result": {"success": success_count}
                })
            except Exception as re:
                logger.error(f"check live sources task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_check_live_task)
        return TaskResponse(data={"task_id": task_id})
    except Exception as e:
        handle_exception(f"check live sources failed: {str(e)}")
