from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Path, Query
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import RedirectResponse

from core.constants import Constants
from core.logger_factory import LoggerFactory
from models.api_request import UpdateLiveRequest
from models.api_response import MiguResponse, TaskResponse
from services.channel import channel_manager
from services.checker import ChannelChecker
from services.task import task_manager
from utils.handler import handle_exception
from utils.parser import parser_manager

router = APIRouter(prefix="/migu", tags=["MIGU工具"])
logger = LoggerFactory.get_logger(__name__)


@router.post("/m3u", summary="自动从migu更新直播源", response_model=TaskResponse)
def update_migu_sources(request: UpdateLiveRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """
    自动更新直播源数据
    """
    try:
        if request.is_clear:
            channel_manager.clear()
            task_manager.clear()

        channel_manager.set_epg(
            url=request.epg.url,
            source=request.epg.source,
            domain=request.epg.domain,
            show_logo=request.epg.show_logo,
            rename_cid=request.epg.rename_cid,
        )

        task_id = task_manager.create_task(
            url="",
            total=0,
            type="update_migu_sources",
            description=f"output: {request.output}",
        )

        def run_update_live_task() -> None:
            """后台运行的批量检查任务"""
            try:
                task_manager.update_task(task_id, status="running", processed=0)
                for url in request.url:
                    if url:
                        parser_manager.load_remote_url_m3u(url, request.group, load_template=False)
                # parser_manager.load_remote_url_migu(task_id,
                #                                     request.epg.file,
                #                                     request.rate_type,
                #                                     request.load_template)
                total_count = channel_manager.total_count()
                task_manager.update_task(task_id, total=total_count, processed=0)

                task_threads = 20
                task = task_manager.get_task(task_id)
                checker = ChannelChecker(task_threads)
                success_count = checker.update_batch_live(
                    threads=task_threads,
                    task_status=task,
                    check_m3u8_invalid=request.check_m3u8,
                    output_file=request.output,
                )
                task.update({"status": "completed", "result": {"success": success_count}})
            except Exception as re:
                logger.error(f"update migu live sources task failed: {str(re)}", exc_info=True)
                task_manager.update_task(task_id, status="error", error=str(re))

        background_tasks.add_task(run_update_live_task)
        return TaskResponse(data={"task_id": task_id})
    except ValueError as ve:
        handle_exception(str(ve), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"update migu live sources request failed: {str(e)}", exc_info=True)
        handle_exception("update migu live sources request failed")


@router.get("/list", summary="获取常量定义的频道列表")
def get_id_list():
    """获取系统中所有频道的列表"""
    try:
        data = Constants.get_migu_list()
        return jsonable_encoder(data)
    except Exception as e:
        handle_exception(f"获取频道列表失败: {str(e)}")


@router.get("/{id}", summary="获取单个频道播放地址")
def parse_channel_url(
    id: str = Path(..., description="频道ID，例如：cctv1"),
    type: Optional[str] = Query(None, description="返回的数据类型，例如：json")
):
    """根据任务ID获取任务详情"""
    channel_id = id  # Constants.get_migu_cid(id)
    channel_name = "Null"
    try:
        chanel_url = parser_manager.get_migu_video_url(channel_name, channel_id, rate_type=3)
        if chanel_url:
            match type:
                case "json":
                    return MiguResponse(url=chanel_url, data={"id": channel_id, "name": channel_name})
                case _:
                    return RedirectResponse(url=chanel_url, status_code=302, headers={
                        'Content-Type': 'application/json;charset=UTF-8'
                    })
    except Exception as e:
        logger.error(f"get {channel_id} video failed: {str(e)}", exc_info=True)

    return MiguResponse(url="", code=101, message="生成播放地址失败", data={"id": channel_id})
