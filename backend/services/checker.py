import concurrent
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse, unquote

import requests
from requests.adapters import HTTPAdapter

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
    def __init__(self, threads, url="", start=0, size=1):
        self._url = url
        self._start = start
        self._size = size

        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=threads,
            pool_maxsize=threads + 10,
            max_retries=1
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @log_execution_time(name=ref("channel_info.name"), url=ref("url_info.url"))
    def check_single_with_timeout(self, channel_info: ChannelInfo, url_info: ChannelUrl, check_m3u8) -> bool:
        logger.debug(f"Checking {channel_info.name} with {url_info.url}")
        try:
            return self._check_single(channel_info, url_info, check_m3u8)
        except Exception as e:
            logger.warning(f"Check for {channel_info.name} failed: {e}")
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

            if not channel_info.name:
                channel_info.set_name(self._extract_channel_name(url_info.url))

        return True

    def _check_mp4_validity(self, url: str, timeout=Constants.REQUEST_TIMEOUT) -> bool:
        try:
            response = requests.head(url, timeout=(5, timeout), allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "video" not in content_type and "mp4" not in content_type:
                return False

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) < 1024:
                return False

            with requests.get(url, stream=True, timeout=(5, timeout)) as partial_response:
                partial_response.raise_for_status()
                iterator = partial_response.iter_content(chunk_size=32)
                try:
                    chunk = next(iterator)
                except StopIteration:
                    return False

                if b"ftyp" in chunk or b"\x00\x00\x00\x18ftyp" in chunk or b"\x00\x00\x00\x20ftyp" in chunk:
                    return True
            return False
        except (requests.Timeout, requests.ConnectionError):
            logger.warning(f"MP4 check timed out/failed for {url}")
            return False
        except Exception as e:
            logger.debug(f"MP4 validity check error: {e}")
            return False

    def _check_m3u8_url(self, url_info: ChannelUrl, timeout=Constants.REQUEST_TIMEOUT):
        try:
            with self.session.get(
                url_info.url,
                timeout=(5, timeout),
                allow_redirects=True,
                stream=True
            ) as response:
                response.raise_for_status()
                content = response.raw.read(1024 * 1024).decode('utf-8', errors='ignore')
                return content
        except Exception as e:
            # logger.debug(f"Request failed: {e}")
            return None

    def get_resolution_ffprobe(self, url: str, timeout=Constants.REQUEST_TIMEOUT) -> int:
        resolution = 0
        ms_timeout = str(timeout * 1000)
        micro_timeout = str(timeout * 1000000)
        try:
            probe_args = [
                'ffprobe',
                '-v', 'quiet',
                '-hide_banner',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=height',
                '-of', 'json',
                '-probesize', '500000',
                '-analyzeduration', '3000000',
                '-connect_timeout', ms_timeout,
                '-rw_timeout', micro_timeout,
                '-stimeout', micro_timeout,
                '-fflags', 'nobuffer',
                '-flags', 'low_delay',
                url
            ]
            result = subprocess.run(
                probe_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout + 2,
                check=True
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                if "streams" in data and data["streams"]:
                    resolution = data["streams"][0].get('height', 0)
        except subprocess.TimeoutExpired:
            logger.warning(f"FFprobe process hard-timeout for {url}")
        except subprocess.CalledProcessError as e:
            logger.debug(f"FFprobe failed to parse {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in ffprobe: {e}")

        return resolution

    def _extract_channel_name(self, url):
        try:
            path = urlparse(url).path
            filename = os.path.basename(path)
            raw_name = unquote(filename).replace('.m3u8', '').replace('.ts', '')

            # 处理 index/playlist 等无意义文件名
            if raw_name.lower() in ['index', 'playlist', 'chunklist', 'video', '']:
                segments = path.strip('/').split('/')
                if len(segments) > 1:
                    return unquote(segments[-2])
            return raw_name
        except Exception as e:
            logger.error(f"Channel name extraction error for {url}: {e}")
            return None

    def check_batch(self, threads, task_status, check_m3u8, check_resolution) -> int:
        task_status_lock = threading.Lock()
        success_count = Counter()
        processed_count = Counter()
        total_count = self._size

        # 如果没有任务直接返回
        if total_count <= 0:
            task_status.update({"progress": 100, "processed": 0, "success": 0})
            return 0

        def check_task(task_args):
            tmp_channel_info, url_info, process_m3u8 = task_args
            try:
                check_result = self.check_single_with_timeout(
                    channel_info=tmp_channel_info,
                    url_info=url_info,
                    check_m3u8=process_m3u8,
                )
                # 验证分辨率逻辑
                if check_result and not url_info.valid_resolution(check_resolution):
                    tmp_channel_info.remove_url(url_info)
                    check_result = False

                return check_result, tmp_channel_info
            except Exception as ex:
                logger.error(f"Error checking {url_info.url}: {ex}")
                return False, None

        optimal_threads = min(threads, os.cpu_count() * Constants.IO_INTENSITY_FACTOR + 1)

        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            # 1. 提交所有任务并获取 future 对象
            future_to_task = {
                executor.submit(check_task, (
                    ChannelInfo(id=str(index)),
                    ChannelUrl(self._url.format(i=index)),
                    check_m3u8
                )): index
                for index in range(self._start, self._start + self._size)
            }

            # 2. 使用 as_completed，谁快谁先更新进度
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    result, channel_info = future.result()
                    if result and channel_info and channel_info.valid():
                        channel_manager.add_channel_info(None, channel_info)
                        success_count.increment()
                except Exception as e:
                    logger.error(f"Task generated an exception: {e}")
                finally:
                    # 3. 无论成功失败都更新进度
                    with task_status_lock:
                        processed_count.increment()
                        p_val = processed_count.get_value()
                        task_status.update({
                            "progress": round(p_val / total_count * 100, 2),
                            "processed": p_val,
                            "success": success_count.get_value(),
                            "updated_at": int(time.time()),
                        })
        channel_manager.sort()
        return success_count.get_value()

    def update_batch_live(self, threads, task_status, check_m3u8_invalid, output_file=None) -> int:
        task_status_lock = threading.Lock()
        success_counter = Counter()
        processed_counter = Counter()

        tasks = []
        for group_name in filter(lambda g: not category_manager.is_ignore(g), channel_manager.get_groups()):
            chanmel_list = channel_manager.get_channel_list(group_name)
            for channel_name in chanmel_list.get_channel_names():
                channel_info = chanmel_list.get_channel(channel_name)
                for url_info in channel_info.get_urls():
                    tasks.append((channel_info, url_info, check_m3u8_invalid))

        total_count = len(tasks)
        task_status["total"] = total_count
        if total_count == 0:
            task_status.update({"progress": 100, "processed": 0, "success": 0})
            return 0

        def process_url(task):
            try:
                task_channel_info, task_url_info, process_m3u8_invalid = task
                check_result = self.check_single_with_timeout(task_channel_info, task_url_info, process_m3u8_invalid)
                if check_result:
                    success_counter.increment()
                else:
                    logger.warning(f"Check for {task_channel_info.name} with {task_url_info.url} invalid")
                    task_channel_info.remove_url(task_url_info)
            except Exception as e:
                logger.error(f"Critical error in process_url: {e}")
            finally:
                current_processed = processed_counter.increment()
                with task_status_lock:
                    task_status.update({
                        "processed": current_processed,
                        "progress": round(current_processed / total_count * 100, 2),
                        "success": success_counter.get_value(),
                        "updated_at": int(time.time()),
                    })

        optimal_threads = min(threads, os.cpu_count() * Constants.IO_INTENSITY_FACTOR + 1)
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            futures = [executor.submit(process_url, t) for t in tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Future unexpected error: {e}")

        final_success = success_counter.get_value()
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
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"## 频道数据导出时间: {timestamp}")
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
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"## 频道数据导出时间: {timestamp}")
            logger.info(f"channel data saved to m3u file {new_file_path}")
        except Exception as e:
            logger.error(f"save data to m3u file error: {e}")
