import threading
from typing import List, Dict, Set

from utils.sort_util import mixed_sort_key


class ChannelUrl:
    """
    频道地址：数据流地址和速度信息
    """
    _instances = {}

    def __new__(cls, url: str, speed=0, resolution=None):
        if url in cls._instances:
            instance = cls._instances[url]
            # 只更新非默认值的属性
            if speed != 0:
                instance.set_speed(speed)
            if resolution is not None:
                instance.set_resolution(resolution)
            return instance
        else:
            instance = super().__new__(cls)
            instance.__init__(url, speed, resolution)
            cls._instances[url] = instance
            return instance

    def __init__(self, url: str, speed=0, resolution=None):
        self.url = url
        self.speed = speed  # 单位：KB/s
        self.resolution = resolution

    def set_url(self, url: str):
        self.url = url

    def set_speed(self, speed):
        self.speed = round(speed, 1)

    def set_resolution(self, resolution):
        self.resolution = resolution

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)


class ChannelInfo:
    """
    频道信息，包括频道数据流地址和速度信息
    """

    def __init__(self, id: str = '', name: str = None):
        self.id = id if id != name else ''
        self.name = name
        self.logo = None
        self.title = '其他'
        self.urls: Set[ChannelUrl] = set()
        self._lock = threading.RLock()

    def set_logo(self, logo: str):
        if logo is not None:
            self.logo = logo

    def set_name(self, name: str):
        self.name = name or f"频道-{self.id}"

    def add_url(self, url: ChannelUrl):
        with self._lock:
            self.urls.add(url)

    def get_urls(self):
        with self._lock:
            return self.urls

    def remove_invalid_url(self, url_info: ChannelUrl):
        with self._lock:
            self.urls.discard(url_info)

    def get_txt(self):
        return '\n'.join(f"{self.name},{url.url}" for url in sorted(self.urls, key=lambda url: url.speed))

    def get_m3u(self, title=''):
        if not title:
            title = self.title

        tvg_id = f"tvg-id=\"{self.id}\" " if self.id != '' else ''
        tvg_logo = f"tvg-logo=\"{self.logo}\" " if self.logo else ''
        return '\n'.join(
            f"#EXTINF:-1 {tvg_id}tvg-name=\"{self.name}\" {tvg_logo}group-title=\"{title}\","
            f"{self.name}\n{url.url}"
            for url in sorted(self.urls, key=lambda url: url.speed)
        )

    def get_all(self, title='') -> str:
        if not title:
            title = self.title
        sorted_urls = sorted(self.urls, key=lambda url: url.speed)
        separator = ['', '===============================================================', '']
        tvg_id = f"tvg-id=\"{self.id}\" " if self.id != '' else ''
        tvg_logo = f"tvg-logo=\"{self.logo}\" " if self.logo else ''
        return ('\n'.join(f"{self.name},{url.url}" for url in sorted_urls) + '\n'
                + '\n'.join(separator) + "\n"
                + '\n'.join(
                    f"#EXTINF:-1 {tvg_id}tvg-name=\"{self.name}\" {tvg_logo}group-title=\"{title}\","
                    f"{self.name}\n{url.url}" for url in sorted_urls)
                )


class ChannelList:
    """
    频道列表，包括多个频道信息
    """

    def __init__(self):
        self._channels: Dict[str, ChannelInfo] = {}
        self._lock = threading.RLock()

    def count(self) -> int:
        with self._lock:
            return sum(len(info.urls) for info in self._channels.values())

    def add_channel(self, channel_name, channel_url: str, id='', logo=None):
        with self._lock:
            if channel_name not in self._channels:
                self._channels[channel_name] = ChannelInfo(id, channel_name)
            channel_info = self._channels[channel_name]
            channel_info.set_logo(logo)
            channel_info.add_url(ChannelUrl(channel_url))

    def add_channel_info(self, channel_info: ChannelInfo):
        with self._lock:
            self._channels[channel_info.name] = channel_info

    def get_channel_names(self):
        with self._lock:
            return self._channels.keys()

    def get_channle_ids(self):
        with self._lock:
            return [channel.id for channel in self._channels.values()]

    def get_channel(self, channel_name) -> ChannelInfo:
        with self._lock:
            if channel_name in self._channels:
                return self._channels.get(channel_name)
        return ChannelInfo()

    def _sorted_channels(self) -> List[ChannelInfo]:
        """
        获取按 ChannelInfo.name 排序后的频道列表
        使用 mixed_sort_key 函数进行智能排序
        """
        with self._lock:
            return sorted(
                self._channels.values(),
                key=lambda channel: mixed_sort_key(channel.name)
            )

    def get_m3u(self, title=''):
        with self._lock:
            return "\n".join(filter(None, (channel_info.get_m3u(title) for channel_info in self._sorted_channels())))

    def get_txt(self):
        with self._lock:
            return '\n'.join(filter(None, (channel_info.get_txt() for channel_info in self._sorted_channels())))

    def write_to_txt_file(self, file_handle):
        with self._lock:
            for channel_info in self._sorted_channels():
                txt_line = channel_info.get_txt()
                if txt_line:
                    file_handle.write(f"{txt_line}\n")

    def write_to_m3u_file(self, group_name, file_handle):
        with self._lock:
            for channel_info in self._sorted_channels():
                m3u_line = channel_info.get_m3u(group_name)
                if m3u_line:
                    file_handle.write(f"{m3u_line}\n")
