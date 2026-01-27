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

    _MIGU_CID_MAP = {
        "CCTV1综合": "cctv1",
        "CCTV2财经": "cctv2",
        "CCTV3综艺": "cctv3",
        "CCTV4中文国际": "cctv4",
        "CCTV5体育": "cctv5",
        "CCTV5+体育赛事": "cctv5plus",
        "CCTV6电影": "cctv6",
        "CCTV7国防军事": "cctv7",
        "CCTV8电视剧": "cctv8",
        "CCTV9纪录": "cctvjilu",
        "CCTV10科教": "cctv10",
        "CCTV11戏曲": "cctv11",
        "CCTV12社会与法": "cctv12",
        "CCTV13新闻": "cctv13",
        "CCTV14少儿": "cctvchild",
        "CCTV15音乐": "cctv15",
        "CCTV17农业农村": "cctv17",
        "CCTV4欧洲": "cctveurope",
        "CCTV4美洲": "cctvamerica",
    }

    @classmethod
    def get_cvt_name(cls, key: str):
        return cls._MIGU_CID_MAP.get(key, key)

    @classmethod
    def cvt_exist(cls, key: str):
        return key in cls._MIGU_CID_MAP
