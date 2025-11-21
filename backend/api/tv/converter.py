import re
from typing import Tuple, Dict

from core.logger_factory import LoggerFactory
from services.channel import ChannelBaseModel
from services.const import Const

logger = LoggerFactory.get_logger(__name__)


class LiveConverter:
    """M3U与TXT格式频道数据相互转换工具"""

    def __init__(self):
        self._channel_model = ChannelBaseModel()

    def m3u_to_txt(self, m3u_data: str) -> str:
        try:
            self._parse_m3u_channels(m3u_data)
            return self._channel_model.to_txt_string()
        except Exception as e:
            logger.exception(f"Failed to parse m3u data: {e}")
            return ""

    def txt_to_m3u(self, txt_data: str) -> str:
        try:
            self._parse_txt_channels(txt_data)
            return self._channel_model.to_m3u_string()
        except Exception as e:
            logger.exception(f"Failed to parse txt data: {e}")
            return ""

    def _parse_m3u_channels(self, m3u_data: str):
        channel_name = None
        channel_id = 0
        group_title = ''

        for line in (line.strip() for line in m3u_data.splitlines() if line.strip()):
            if line.startswith('#EXTM3U'):
                continue

            if line.startswith('#EXTINF:'):
                tag_content = line[8:].strip()
                params, name = LiveConverter.parse_extinf_params(tag_content)
                channel_name = Const.get_channel(name)
                try:
                    channel_id = params.get('id') if "id" in params else '0'
                except ValueError:
                    channel_id = ''
                group_title = params.get('title', '')

            elif line.startswith(('http:', 'https:')):
                self._channel_model.add_channel(
                    name=group_title,
                    channel_name=channel_name,
                    channel_url=line,
                    id=channel_id)

    @staticmethod
    def parse_extinf_params(content: str) -> Tuple[Dict, str]:
        """解析EXTINF标签中的参数和频道名称"""
        params = {}
        name = ''

        param_str, *name_parts = content.rsplit(',', 1)
        if name_parts:
            name = name_parts[0].strip()

        param_pattern = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')
        for match in param_pattern.finditer(param_str):
            params[match.group(1)] = match.group(2)

        return params, name

    def _parse_txt_channels(self, txt_data: str):
        group_title = '其他'
        for line in txt_data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.endswith('#genre#'):
                group_title = line[:-8].strip()
                continue

            name, url = line.split(',', 1)
            self._channel_model.add_channel(name=group_title, channel_name=name, channel_url=url)
