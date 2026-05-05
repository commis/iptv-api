import json
import time
from typing import Dict, List
from urllib.parse import urlencode

import httpx

from core.logger_factory import LoggerFactory
from models.counter import Counter
from services import config_manager
from services.redis import redis_client

logger = LoggerFactory.get_logger(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}


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

    async def collect_all_videos(self, task_status, is_full: bool = False):
        total_count = task_status["total"]
        success = Counter()
        failed = Counter()
        processed = Counter()
        skipped = Counter()

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            site_config = config_manager.video_vod_config
            for cat_name, video_names in site_config.site_videos.items():
                for video_name in video_names:
                    current_processed = processed.increment()
                    redis_key = f"tv-vod:{cat_name}:{video_name}"
                    if not is_full and self.redis_get(redis_key):
                        skipped.increment()
                        continue

                    video_data = await self._collect_detail(client, video_name)
                    if video_data:
                        self.redis_set(redis_key, video_data)
                        success.increment()
                        logger.debug(f"采集完成：{cat_name}/{video_name}")
                    else:
                        failed.increment()
                        logger.warning(f"采集失败：{cat_name}/{video_name}")

                    task_status.update({
                        "processed": current_processed,
                        "progress": round(current_processed / total_count * 100, 2),
                        "success": success.get_value(),
                        "updated_at": int(time.time()),
                    })

        # 存在跳过处理，最终刷新一次状态
        task_status.update({
            "processed": current_processed,
            "progress": round(current_processed / total_count * 100, 2),
            "success": success.get_value(),
            "updated_at": int(time.time()),
        })
        return {
            "fail": failed.get_value(),
            "success": success.get_value(),
            "skipped": skipped.get_value()
        }

    async def _collect_detail(self, client: httpx.AsyncClient, video_name: str):
        site_config = config_manager.video_vod_config
        for site in site_config.site_collections:
            try:
                params = {"ac": "detail", "wd": video_name}
                url = f"{site}?{urlencode(params)}"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data and len(data.get("list", [])) > 0:
                    data_list = self.filter_list(data["list"])
                    for video in data_list:
                        if video.get("vod_name") == video_name:
                            return video
            except Exception:
                continue
        return None
