import concurrent
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Tuple
from urllib.parse import urljoin

import m3u8
import requests
from requests import Timeout

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
    def check_single_with_timeout(self, channel_info: ChannelInfo, url_info: ChannelUrl,
                                  check_sub_m3u8, timeout=60) -> bool:
        """带超时控制的频道检测方法"""
        logger.debug(f"Checking {channel_info.name} with {url_info.url}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._check_single, channel_info, url_info, check_sub_m3u8)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                # 超时发生时，future会被自动取消
                logger.warning(
                    f"Check for {channel_info.name} with {url_info.url} timed out after {timeout} seconds")
                return False
            except Exception as e:
                logger.error(f"check_single error: {e}")
                return False

    def _check_single(self, channel_info: ChannelInfo, url_info: ChannelUrl, check_sub_m3u8) -> bool:
        if url_info.url.endswith(".mp4"):
            return self._check_mp4_validity(url_info.url)

        if ".m3u8" not in url_info.url:
            return False

        if check_sub_m3u8:
            # 第一阶段：基础验证
            m3u8_content = self._check_m3u8_url(url_info)
            if not m3u8_content:
                return False

            # 第二阶段：结构验证
            is_valid, reason = self._check_m3u8_validity(m3u8_content)
            if not is_valid:
                logger.debug(f"M3U8 structure invalid for {channel_info.name} with {url_info.url}: {reason}")
                return False

            # 第三阶段：TS验证
            base_url = url_info.url.rsplit('/', 1)[0]
            ts_urls = self._extract_ts_urls(m3u8_content)
            ts_valid, ts_reason, tested_urls = self._check_ts_availability(ts_urls, base_url)
            if not ts_valid:
                logger.debug(f"TS segments invalid for {channel_info.name} with {url_info.url}: {ts_reason}")
                return False

            # 第四阶段：测速
            url_info.set_speed(self._benchmark_speed(tested_urls))

            # 第五阶段：元数据提取
            if not channel_info.name:
                channel_info.set_name(self._extract_channel_name(m3u8_content, url_info.url))

        return True

    def _check_mp4_validity(self, url: str, timeout=Constants.REQUEST_TIMEOUT) -> bool:
        """MP4 播放有效性检查"""
        try:
            response = requests.head(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type')
            if content_type and 'video/mp4' not in content_type.lower():
                return False

            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) < 1024:
                return False

            partial_response = requests.get(url, stream=True, timeout=timeout)
            partial_response.raise_for_status()
            # 读取前 8Bit 内容，检查是否包含 MP4 头部信息
            chunk = partial_response.raw.read(8)
            partial_response.close()
            # MP4 文件以 0x00000018 或 0x00000020 开头，后跟 "ftyp" 字符串
            if b'\x00\x00\x00\x18ftyp' in chunk or b'\x00\x00\x00\x20ftyp' in chunk:
                return True
            return False
        except:
            return False

    def _check_m3u8_url(self, url_info: ChannelUrl, timeout=Constants.REQUEST_TIMEOUT):
        """带超时的m3u8 URL检查，支持递归解析子m3u8"""
        try:
            response = requests.get(url_info.url, timeout=(2, timeout - 2))
            response.raise_for_status()
            content = response.text

            if '#EXT-X-STREAM-INF' in content:
                # 使用正则表达式提取所有流信息和路径
                for match in re.finditer(r'#EXT-X-STREAM-INF:.*?\n(.+)', content):
                    child_m3u8 = match.group(1).strip()
                    url_info.set_url(child_m3u8
                                     if child_m3u8.startswith('http')
                                     else urljoin(url_info.url, child_m3u8))
                    child_content = self._check_m3u8_url(url_info)
                    if child_content:
                        content = child_content
                        break

            return content
        except:
            return None

    def _check_m3u8_validity(self, m3u8_content):
        """增强版M3U8有效性验证"""
        # 基础验证
        if not m3u8_content.startswith("#EXTM3U"):
            return False, "missing #EXTM3U header"

        # 结构验证
        required_tags = ["#EXT-X-VERSION", "#EXT-X-MEDIA-SEQUENCE"]
        missing_tags = [tag for tag in required_tags if tag not in m3u8_content]
        if missing_tags:
            return False, f"missing required tags: {', '.join(missing_tags)}"

        return True, "结构完整"

    def _check_ts_availability(self, ts_urls, base_url):
        """带超时和并发的TS片段检查"""
        success = Counter()
        max_test_count = min(len(ts_urls), Constants.TS_SEGMENT_TEST_COUNT)

        # 使用线程池并发测试TS片段
        with ThreadPoolExecutor(max_workers=max_test_count) as executor:
            futures = []
            tested_urls = []

            for ts in ts_urls[:max_test_count]:
                full_url = ts if ts.startswith('http') else urljoin(
                    base_url if base_url.endswith('/') else base_url + '/', ts)
                futures.append(executor.submit(self._validate_ts, full_url, timeout=Constants.REQUEST_TIMEOUT))

            # 带超时的结果处理
            for future in as_completed(futures):
                try:
                    ts_url, is_valid = future.result(timeout=30)
                    if is_valid:
                        success.increment()
                        tested_urls.append(ts_url)
                except Exception as e:
                    logger.debug(f"TS check error: {e}")

        if success.get_value() == 0:
            return False, "all ts segments are not available", []
        return True, f"{success.get_value()}/{max_test_count} segments are available.", tested_urls

    def _validate_ts(self, url, timeout) -> Tuple[str, bool]:
        """带超时的TS片段验证"""
        try:
            # 只获取头部信息，减少数据传输
            response = requests.head(url, timeout=(1, timeout - 1), allow_redirects=True)
            response.raise_for_status()
            return url, response.status_code == 200
        except Exception as e:
            logger.debug(f"_validate_ts error: {e}")
            return url, False

    def _extract_ts_urls(self, m3u8_content):
        m3u8_obj = m3u8.loads(m3u8_content)
        return m3u8_obj.segments.uri

    def _benchmark_speed(self, ts_urls, timeout=Constants.REQUEST_TIMEOUT):
        """带超时的TS片段测速"""
        total_size = 0
        total_time = 0

        session = requests.Session()
        for url in ts_urls:
            try:
                with session.get(url, stream=True, timeout=timeout) as res:
                    res.raise_for_status()
                    # 精确读取前512KB数据并计时
                    start = time.time()
                    data_chunks = res.iter_content(1024)
                    size = sum(len(chunk) for chunk, _ in zip(data_chunks, range(512)))
                    elapsed = time.time() - start

                    total_size += size
                    total_time += elapsed
            except:
                continue

        session.close()
        return 0 if total_time == 0 else (total_size / total_time) / 1024

    def _extract_channel_name(self, m3u8_content, url, timeout=3):
        """带超时的频道名称提取"""

        def get_channel_name_worker(m3u8_info, request_url):
            """频道名称提取的实际工作函数"""
            # 方案1: 从EXTINF行提取
            channel_name = self._extract_from_extinf(m3u8_info)
            if channel_name:
                return channel_name

            # 方案2: 从Content-Disposition头提取 - 增加超时控制
            channel_name = self._extract_from_content_disposition(request_url, timeout=2)
            if channel_name:
                return channel_name

            return None

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_channel_name_worker, m3u8_content, url)
            try:
                return future.result(timeout=timeout)
            except Exception as e:
                logger.error(f"Channel name extraction error: {e}")
                return None

    def _extract_from_extinf(self, m3u8_content):
        """
        强化版EXTINF解析逻辑（禁止使用TS文件名）
        匹配策略：
        1. 优先捕获 tvg-name 属性
        2. 捕获逗号后的显示名称
        3. 无有效名称时返回None
        """
        extinf_pattern = re.compile(
            r'^#EXTINF:\s*'
            r'(?P<duration>-?\d+\.?\d*)\s*'  # 捕获时长
            r'(?:tvg-name=(?P<qt1>[\'"]?)(?P<tvg_name>[^\'",#]+?)(?P=qt1)\s*)?'  # 修复括号
            r'(?:,?\s*(?P<display_name>[^#]+?))?'  # 显示名称
            r'\s*(?:#.*)?$',  # 注释部分
            re.IGNORECASE | re.MULTILINE
        )
        remove_chars = str.maketrans('', '', ',.，。')

        candidates = []
        for line in m3u8_content.splitlines():
            if not line.startswith('#EXTINF'):
                continue

            match = extinf_pattern.match(line)
            if not match:
                continue

            groups = match.groupdict()
            # 优先级1：tvg-name（带/不带引号）
            if groups['tvg_name']:
                clean_name = groups['tvg_name'].strip('\'"')
                if clean_name:
                    return clean_name

            # 优先级2：显示名称（需清洗）
            if groups['display_name']:
                display = groups['display_name'].strip()
                # 过滤无效名称（纯数字、空值等）
                cleaned_display = display.translate(remove_chars)
                if cleaned_display:
                    candidates.append(display)

        # 选择最优显示名称（最长非空值）
        if candidates:
            return max(candidates, key=lambda x: len(x))

        return None

    def _extract_from_content_disposition(self, url, timeout=2):
        """带超时的Content-Disposition提取"""
        try:
            response = requests.head(url, timeout=(1, timeout - 1), allow_redirects=True)
            if 'content-disposition' in response.headers:
                cd_header = response.headers['content-disposition']
                filename_match = re.findall("filename=(.+)", cd_header)
                if filename_match:
                    filename = filename_match[0].strip('";')
                    return os.path.splitext(filename)[0]
        except (Timeout, ConnectionError):
            pass
        except Exception as e:
            logger.error(f"extract_from_content_disposition error: {e}")

        return None

    def check_batch(self, threads, task_status, check_sub_m3u8) -> int:
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
                yield tmp_channel_info, url_info, check_sub_m3u8

        def check_task(args):
            tmp_channel_info, url_info, process_sub_m3u8 = args
            try:
                return (self.check_single_with_timeout(channel_info=tmp_channel_info,
                                                       url_info=url_info,
                                                       check_sub_m3u8=process_sub_m3u8), tmp_channel_info)
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
                if result and channel_info:
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
                    channel_info.remove_invalid_url(url_info)
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
        optimal_threads = min(threads, os.cpu_count() * Constants.IO_INTENSITY_FACTOR + 1)
        with ThreadPoolExecutor(max_workers=optimal_threads) as executor:
            def task_generator():
                actual_count = 0
                # 部分分类组忽略不予处理
                for group_name in filter(lambda g: not category_manager.is_ignore(g), channel_manager.get_groups()):
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
            with open(file_path, 'w', encoding='utf-8') as f:
                # 添加时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# 频道数据导出时间: {timestamp}\n")
                channel_manager.write_to_txt_file(f)
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

        new_file_path = replace_file_extension(file_path, '.m3u')
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

            # 写入数据
            with open(new_file_path, 'w', encoding='utf-8') as f:
                # 添加时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# 频道数据导出时间: {timestamp}\n")
                channel_manager.write_to_m3u_file(f)
            logger.info(f"channel data saved to m3u file {new_file_path}")
        except Exception as e:
            logger.error(f"save data to m3u file error: {e}")
