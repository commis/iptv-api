# constants.py
import re


class Constants:
    """项目公共常量类，包含所有业务需要的常量定义"""

    # 合并正则：移除表情符号、逗号、#genre#和多余空格
    CATEGORY_CLEAN_PATTERN = re.compile(
        r'[\U0001F000-\U0001FFFF\U00002500-\U00002BEF\U00002E00-\U00002E7F\U00003000-\U00003300,#genre#\s]+')

    # 网络请求相关常量
    REQUEST_TIMEOUT = 5  # 网络请求超时时间（秒）

    # 线程池相关常量
    IO_INTENSITY_FACTOR = 4  # 可在2-8之间调整

    # M3U8解析相关常量
    TS_SEGMENT_TEST_COUNT = 3  # 测试TS片段数量，建议小于4个
