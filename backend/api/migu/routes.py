from fastapi import APIRouter, BackgroundTasks, Path
from fastapi.encoders import jsonable_encoder
from starlette import status

from core.constants import Constants
from core.logger_factory import LoggerFactory
from models.api_request import UpdateLiveRequest
from models.api_response import MiguResponse, TaskResponse
from services.channel import channel_manager
from services.checker import ChannelChecker
from services.task import task_manager
from utils.handler import handle_exception
from utils.parser import Parser, parser_manager

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
                task = task_manager.get_task(task_id)
                task_manager.update_task(task_id, status="running")

                parser = Parser()
                parser.load_remote_url_migu(task_id, request.epg.file, request.rate_type)
                total_count = channel_manager.total_count()
                task_manager.update_task(task_id, total=total_count, processed=0)

                checker = ChannelChecker()
                success_count = checker.update_batch_live(
                    threads=20,
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


@router.get("/list", summary="获取所有频道列表")
def get_id_list():
    """获取系统中所有频道的列表"""
    try:
        data = Constants.get_migu_list()
        return jsonable_encoder(data)
    except Exception as e:
        handle_exception(f"获取频道列表失败: {str(e)}")


@router.get("/{id}", summary="解析单个频道播放地址")
def parse_channel_url(id: str = Path(..., description="频道ID，例如：cctv1")):
    """根据任务ID获取任务详情"""
    channel_id = Constants.get_migu_cid(id)
    chanel_url = parser_manager.get_migu_video_url("Null", channel_id)
    if chanel_url:
        return MiguResponse(url=chanel_url, data={"id": channel_id})
    return MiguResponse(url=chanel_url, code=101, message="生成播放地址失败", data={"id": channel_id})
