import os
import re
from typing import Dict

import requests
import yaml

from core.constants import Constants
from core.logger_factory import LoggerFactory
from core.singleton import singleton

logger = LoggerFactory.get_logger(__name__)


@singleton
class SubscribeService:

    def __init__(self):
        self._sub_url = "http://107.174.95.154:25500/sub"
        self._config = "config/ACL4SSR_Online_Mini_MultiMode.ini"
        self._params = "clash.dns=1&insert=false&emoji=true&new_name=true&flag=meta"
        self._tmp_path = "https://ak3721.top/clash/node"
        self._tmp_url = "/app/node"

        self._urls: Dict[str, str] = {
            # https://github.com/ssrsub/ssr
            "ssrsub": "https://raw.githubusercontent.com/ssrsub/ssr/master/clash.yaml",
            # https://github.com/go4sharing/sub
            "subsub": "https://raw.githubusercontent.com/go4sharing/sub/main/sub.yaml"
        }

    def get_clash_subscribe(self, clash_key: str) -> str:
        url = self._urls.get(clash_key)
        if not url:
            logger.error(f"unsupported subscribe key: {clash_key}")
            return ""

        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT, verify=False)
            response.raise_for_status()

            yaml_data = yaml.safe_load(response.text)
            proxies = yaml_data.get("proxies", []) if isinstance(yaml_data, dict) else []
            for proxy in proxies:
                if proxy.get("name"):
                    proxy["name"] = self._format_name(proxy["name"])

            os.makedirs(self._tmp_url, exist_ok=True)
            clash_file = os.path.join(self._tmp_url, f"clash_{clash_key}.yaml")
            with open(clash_file, "w", encoding="utf-8") as f:
                yaml.safe_dump({"proxies": proxies}, f, allow_unicode=True)

            proxies_url = f"{self._tmp_path}/{os.path.basename(clash_file)}"
            return self._convert_to_clash(proxies_url)
        except Exception as e:
            logger.error(f"get clash subscribe failed: {e}")
            return ""

    def _format_name(self, name: str) -> str:
        """格式化节点名称：
        去 emoji/"机场推荐:xxx"前缀；"-"分隔符前后去空格；结尾序号补零并保留一个空格
        """
        name = re.sub(r'^[\U0001F1E6-\U0001F1FF]{2}\s*|机场推荐:\S*\s*', '', name)
        name = re.sub(r'\s*-\s*', '-', name)
        return re.sub(r'-(\d+)$', lambda m: ' ' + m.group(1).zfill(2), name)

    def _convert_to_clash(self, proxies_url: str) -> str:
        url = f"{self._sub_url}?target=clash&url={proxies_url}&config={self._config}&{self._params}"
        try:
            response = requests.get(url, timeout=Constants.REQUEST_TIMEOUT, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"convert ssrsub to clash failed: {e}")
            return ""


subscribe_service = SubscribeService()