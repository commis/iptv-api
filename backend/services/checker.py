import concurrent
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

import requests

from core.constants import Constants
from core.execution_time import log_execution_time, ref
from core.logger_factory import LoggerFactory
from models.channel_info import ChannelInfo, ChannelUrl
from models.counter import Counter
from services import channel_manager, category_manager

logger = LoggerFactory.get_logger(__name__)


class TimeoutException(Exception):
    """自定义超时异常"""
    pass


class ChannelChecker:
    def __init__(self, url="", start=0, size=1):
        self._url = url
        self._start = start
        self._size = size

    @log_execution_time(name=ref("channel_info.name"), url=ref("url_info.url"))
    def check_single_with_timeout(self, channel_info: ChannelInfo, url_info: ChannelUrl, check_m3u8,
                                  timeout=60) -> bool:
        """带超时控制的频道检测方法"""
        logger.debug(f"Checking {channel_info.name} with {url_info.url}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._check_single, channel_info, url_info, check_m3u8)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                # 超时发生时，future会被自动取消
                logger.warning(f"Check for {channel_info.name} with {url_info.url} timed out after {timeout} seconds")
                return False
            except Exception as e:
                logger.error(f"check_single error: {e}")
                return False

    def _check_single(self, channel_info: ChannelInfo, url_info: ChannelUrl, check_m3u8) -> bool:
        if url_info.url.endswith(".mp4"):
            return self._check_mp4_validity(url_info.url)

        if check_m3u8:
            m3u8_content = self._check_m3u8_url(url_info)
            if not m3u8_content:
                # logger.error(f"Check for {channel_info.name} with {url_info.url} m3u8 is empty")
                return False

            url_info.set_resolution(self.get_resolution_ffprobe(url_info.url))
            # url_info.set_speed(self._benchmark_speed(tested_urls))

            # 第五阶段：元数据提取
            if not channel_info.name:
                channel_info.set_name(self._extract_channel_name(url_info.url))

        return True

    def _check_mp4_validity(self, url: str, timeout=Constants.REQUEST_TIMEOUT) -> bool:
        """MP4 播放有效性检查"""
        try:
            response = requests.head(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type")
            if content_type and "video/mp4" not in content_type.lower():
                return False

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) < 1024:
                return False

            partial_response = requests.get(url, stream=True, timeout=timeout)
            partial_response.raise_for_status()
            # 读取前 8Bit 内容，检查是否包含 MP4 头部信息
            chunk = partial_response.raw.read(8)
            partial_response.close()
            # MP4 文件以 0x00000018 或 0x00000020 开头，后跟 "ftyp" 字符串
            if b"\x00\x00\x00\x18ftyp" in chunk or b"\x00\x00\x00\x20ftyp" in chunk:
                return True
            return False
        except Exception as e:
            return False

    def _check_m3u8_url(self, url_info: ChannelUrl, timeout=Constants.REQUEST_TIMEOUT):
        """带超时的m3u8 URL检查，支持递归解析子m3u8"""
        try:
            response = requests.get(url_info.url, timeout=(timeout, timeout + 2))
            response.raise_for_status()
            return response.text
        except:
            return None

    def get_resolution_ffprobe(self, url: str, headers: dict = None, timeout=Constants.REQUEST_TIMEOUT) -> int:
        resolution = 0
        try:
            headers_str = ''.join(f'{k}: {v}\r\n' for k, v in headers.items()) if headers else ''
            probe_args = [
                'ffprobe',
                '-v', 'error',
                '-headers', headers_str,
                '-connect_timeout', '5000',
                '-rw_timeout', '5000000',
                '-probesize', '32768',
                '-analyzeduration', '1000000',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                "-of", 'json',
                url
            ]

            result = subprocess.run(probe_args, capture_output=True, text=True, timeout=timeout, check=True)
            data = json.loads(result.stdout)
            if "streams" in data and len(data["streams"]) > 0:
                video_stream = data["streams"][0]
                resolution = video_stream['height']
        except Exception as e:
            pass

        return resolution

    def _extract_channel_name(self, url, timeout=5):
        """带超时的频道名称提取"""

        def get_channel_name_worker(m3u8_url) -> str:
            path = urlparse(m3u8_url).path
            filename = os.path.basename(path)
            raw_name = unquote(filename).replace('.m3u8', '').replace('.ts', '')
            if raw_name.lower() in ['index', 'playlist', 'chunklist', 'video', '']:
                segments = path.strip('/').split('/')
                if len(segments) > 1:
                    return unquote(segments[-2])
            return raw_name

        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(get_channel_name_worker, url)
                return future.result(timeout=timeout)
            except Exception as e:
                logger.error(f"Channel name extraction error: {e}")
                return None

    def check_batch(self, threads, task_status, check_m3u8, check_resolution) -> int:
        task_status_lock = threading.Lock()
        success_count = Counter()
        processed_count = Counter()
        total_count = self._size

        # 生成器函数：逐个生成任务，避免一次性创建所有任务列表
        def task_generator():
            for index in range(self._start, self._start + self._size):
                url_info = ChannelUrl(self._url.format(i=index))
                tmp_channel_info = ChannelInfo(id=str(index))
                tmp_channel_info.add_url(url_info)
                yield tmp_channel_info, url_info, check_m3u8

        def check_task(args):
            tmp_channel_info, url_info, process_m3u8 = args
            try:
                check_result = self.check_single_with_timeout(
                    channel_info=tmp_channel_info,
                    url_info=url_info,
                    check_m3u8=process_m3u8,
                )
                if not url_info.valid_resolution(check_resolution):
                    tmp_channel_info.remove_url(url_info)

                return check_result, tmp_channel_info
            except TimeoutException as te:
                logger.warning(f"Timeout checking {url_info.url}: {te}")
                return False, None
            except Exception as e:
                logger.error(f"Error checking {url_info.url}: {e}")
                return False, None

        # 使用生成器和并行处理
        optimal_threads = min(threads, os.cpu_count() * Constants.IO_INTENSITY_FACTOR + 1)
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            # 使用chunksize提高I/O密集型任务效率
            results = executor.map(check_task, task_generator(), chunksize=max(1, total_count // 10))
            for result, channel_info in results:
                if result and channel_info and channel_info.valid():
                    channel_manager.add_channel_info(None, channel_info)
                    success_count.increment()

                with task_status_lock:
                    processed_count.increment()
                    task_status.update({
                        "progress": round(processed_count.get_value() / total_count * 100, 2),
                        "processed": processed_count.get_value(),
                        "success": success_count.get_value(),
                        "updated_at": int(time.time()),
                    })
        channel_manager.sort()
        return success_count.get_value()

    def update_batch_live(self, threads, task_status, check_m3u8_invalid, output_file=None) -> int:
        """批量更新直播频道信息"""
        task_status_lock = threading.Lock()
        success_counter = Counter()
        processed_counter = Counter()
        total_count = task_status["total"]

        def process_url(task):
            channel_info, url_info, process_m3u8_invalid = task
            check_result = self.check_single_with_timeout(channel_info, url_info, process_m3u8_invalid)
            try:
                if check_result:
                    success_counter.increment()
                else:
                    logger.warning(f"Check for {channel_info.name} with {url_info.url} invalid")
                    channel_info.remove_url(url_info)
            finally:
                with task_status_lock:
                    processed_counter.increment()
                    processed = processed_counter.get_value()
                    task_status.update({
                        "progress": round(processed / total_count * 100, 2),
                        "processed": processed,
                        "success": success_counter.get_value(),
                        "updated_at": int(time.time()),
                    })

        # 生成任务并立即处理
        optimal_threads = min(
            threads, os.cpu_count() * Constants.IO_INTENSITY_FACTOR + 1
        )
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:

            def task_generator():
                actual_count = 0
                # 部分分类组忽略不予处理
                for group_name in filter(
                        lambda g: not category_manager.is_ignore(g),
                        channel_manager.get_groups(),
                ):
                    chanmel_list = channel_manager.get_channel_list(group_name)
                    channel_name_list = chanmel_list.get_channel_names()
                    for channel_name in channel_name_list:
                        channel_info = chanmel_list.get_channel(channel_name)
                        url_list = list(channel_info.get_urls())
                        actual_count += len(url_list)
                        for url_info in url_list:
                            yield channel_info, url_info, check_m3u8_invalid
                # 验证实际任务数
                nonlocal total_count
                if actual_count != total_count:
                    logger.warning(f"Actual task count ({actual_count}) differs from expected total ({total_count})")
                    total_count = actual_count
                    task_status["total"] = total_count
                return actual_count

            # 提交所有任务
            futures = [executor.submit(process_url, task) for task in task_generator()]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"future result error: {e}")

        # 最终状态验证
        final_processed = processed_counter.get_value()
        final_success = success_counter.get_value()
        logger.info(f"Final status: Total={total_count}, Processed={final_processed}, Success={final_success}")

        self._write_data_to_txt_file(output_file)
        self._write_data_to_m3u_file(output_file)
        return final_success

    def _write_data_to_txt_file(self, file_path):
        """将分组管理器中的频道信息保存到文件"""
        if not file_path:
            return
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 写入数据
            with open(file_path, "w", encoding="utf-8") as f:
                channel_manager.write_to_txt_file(f)
                # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # f.write(f"# 频道数据导出时间: {timestamp}")
            logger.info(f"channel data saved to txt file {file_path}")
        except Exception as e:
            logger.error(f"save data to txt file error: {e}")

    def _write_data_to_m3u_file(self, file_path):
        """将分组管理器中的频道信息保存到文件"""

        def replace_file_extension(target_path, new_ext):
            file_name, _ = os.path.splitext(target_path)
            return file_name + new_ext

        if not file_path:
            return

        new_file_path = replace_file_extension(file_path, ".m3u")
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

            # 写入数据
            with open(new_file_path, "w", encoding="utf-8") as f:
                channel_manager.write_to_m3u_file(f)
                # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # f.write(f"# 频道数据导出时间: {timestamp}")
            logger.info(f"channel data saved to m3u file {new_file_path}")
        except Exception as e:
            logger.error(f"save data to m3u file error: {e}")
