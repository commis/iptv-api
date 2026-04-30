import json
from typing import Dict, List
from urllib.parse import urlencode

import httpx

from core.logger_factory import LoggerFactory
from services import config_manager
from services.redis import redis_client

logger = LoggerFactory.get_logger(__name__)


class VideoCollector:

    @staticmethod
    def filter_fields(raw_item: Dict) -> Dict:
        """统一过滤：只保留需要的字段，全局唯一标准"""
        return {
            "vod_id": raw_item.get("vod_id", ""),
            "vod_name": raw_item.get("vod_name", ""),
            "vod_pic": raw_item.get("vod_pic", ""),
            "type_name": raw_item.get("type_name", ""),
            "vod_remarks": raw_item.get("vod_remarks", ""),
            "vod_year": raw_item.get("vod_year", ""),
            "vod_area": raw_item.get("vod_area", ""),
            "vod_director": raw_item.get("vod_director", ""),
            "vod_actor": raw_item.get("vod_actor", ""),
            "vod_content": raw_item.get("vod_content", ""),
            "vod_play_from": raw_item.get("vod_play_from", ""),
            "vod_play_url": raw_item.get("vod_play_url", "")
        }

    @staticmethod
    def filter_list(raw_list: List[Dict]) -> List[Dict]:
        """批量过滤列表"""
        return [VideoCollector.filter_fields(item) for item in raw_list]

    @staticmethod
    def redis_set(key: str, data: Dict):
        json_str = json.dumps(data, ensure_ascii=False)
        redis_client.set(key, json_str)

    @staticmethod
    def redis_get(key: str) -> Dict | None:
        data_str = redis_client.get(key)
        if not data_str:
            return None
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None

    async def collect_all_videos(self, update: bool = False):
        total = 0
        success = 0
        skipped = 0

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            for cat_name, video_names in config_manager.site_videos.items():
                for video_name in video_names:
                    total += 1
                    redis_key = f"tv-vod:{cat_name}:{video_name}"

                    if not update and self.redis_get(redis_key):
                        skipped += 1
                        continue

                    data = await self._collect_detail(client, video_name)
                    if data and data.get("list"):
                        # remaid_data = {"list": self.filter_list(data["list"])}
                        remaid_data = self.filter_fields(data["list"][0])
                        self.redis_set(redis_key, remaid_data)
                        success += 1
                        logger.info(f"采集完成：{cat_name}/{video_name}")
                    else:
                        logger.warning(f"采集失败：{cat_name}/{video_name}")

        return {
            "total": total,
            "success": success,
            "skipped": skipped,
            "update_mode": update
        }

    async def _collect_detail(self, client: httpx.AsyncClient, video_name: str):
        for site in config_manager.site_collections:
            try:
                params = {"ac": "detail", "wd": video_name}
                url = f"{site}?{urlencode(params)}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data and len(data.get("list", [])) > 0:
                    return data
            except Exception:
                continue
        return None
