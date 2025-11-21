import requests
from bs4 import BeautifulSoup

from api.tv.converter import LiveConverter
from core.constants import Constants
from core.logger_factory import LoggerFactory
from services import channel_manager, category_manager
from services.const import Const

logger = LoggerFactory.get_logger(__name__)


class Parser:
    _live_url = "http://107.174.95.154/tvbox/json/live.txt"

    @staticmethod
    def get_channel_data(text_data: str) -> list:
        """
        将用户提供的频道数据文本解析为 [(类别, 子类型, URL), ...] 格式的元组列表
        """
        category_stack = None
        channel_list = []

        for line in text_data.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.endswith('#genre#'):
                category = Constants.CATEGORY_CLEAN_PATTERN.sub(' ', line[:-7]).strip()
                category_stack = Const.get_category(category) if category else None
                continue

            if category_stack:
                parts = line.split(',', 1)
                if len(parts) != 2:
                    continue
                channel_name, url = [p.strip() for p in parts]
                if not url:
                    continue

                category_info = category_manager.get_category_object(channel_name, category_stack)
                category_name = category_info.get('name')
                if not category_manager.is_exclude(category_info, channel_name):
                    channel_list.append((category_name, channel_name, url))

        return channel_list

    def load_remote_sitemap(cls, url: str):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'xml')
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                if not url.endswith("iptv4.txt"):
                    continue
                cls.load_remote_url_txt(url, True)

            # 处理自建频道
            cls.load_remote_url_txt(cls._live_url)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"parse sitemap data failed: {e}")

    def load_remote_url_txt(cls, url, use_ignore=False):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            cls.load_channel_txt(response.text.strip(), use_ignore)
        except Exception as e:
            logger.error(f"access remote url data failed: {e}")

    @staticmethod
    def load_channel_txt(text_data, use_ignore: bool = False):
        from services import category_manager

        category_name = None
        for line in (line.strip() for line in text_data.splitlines() if line.strip() and not line.startswith('#')):
            if line.endswith('#genre#'):
                category_name = None
                parse_category = Constants.CATEGORY_CLEAN_PATTERN.sub(' ', line).strip()
                define_category = Const.get_category(parse_category)
                if define_category is None or (use_ignore and category_manager.is_ignore(define_category)):
                    continue
                if category_manager.exists(define_category):
                    category_name = define_category
                continue

            if category_name:
                # 解析频道信息
                try:
                    subgenre, url = line.split(',', 1)
                    subgenre, url = subgenre.strip(), url.strip()
                    channel_name = Const.get_channel(subgenre)
                    if url:
                        channel_manager.add_channel(category_name, channel_name, url)
                except ValueError:
                    continue

    def load_remote_url_m3u(cls, url: str):
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT)
            response.raise_for_status()
            m3u_data = response.text.strip()

            tvg_id = ''
            tvg_logo = ''
            group_title = ''
            channel_name = None
            for line in (line.strip() for line in m3u_data.splitlines() if line.strip()):
                if line.startswith('#EXTM3U'):
                    continue

                if line.startswith('#EXTINF:'):
                    tag_content = line[8:].strip()
                    params, name = LiveConverter.parse_extinf_params(tag_content)
                    channel_name = Const.get_channel(name)
                    tvg_id = Const.get_channel(params.get('id', ''))
                    tvg_logo = params.get('logo', '')
                    group_title = params.get('title', '')

                elif line.startswith(('http:', 'https:')):
                    define_category = Const.get_category(group_title)
                    if (define_category is None
                            or (category_manager.is_ignore(define_category))
                            or not category_manager.exists(define_category)):
                        continue
                    tvg_new_logo = channel_manager.epg.get_logo(tvg_logo)
                    channel_manager.add_channel(define_category, channel_name, line, tvg_id, tvg_new_logo)

            # 处理自建频道
            cls.load_remote_url_txt(cls._live_url)
            channel_manager.sort()
        except Exception as e:
            logger.error(f"parse m3u data failed: {e}")
