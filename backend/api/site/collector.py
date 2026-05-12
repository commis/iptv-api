import json
import time
from typing import Dict, List
from urllib.parse import urlencode

import httpx

from core.logger_factory import LoggerFactory
from services import config_manager
from services.redis import redis_client

logger = LoggerFactory.get_logger(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}


class VideoCollector:

    @staticmethod
    def filter_base_fields(raw_item: Dict) -> Dict:
        return {
            "vod_name": raw_item.get("vod_name", ""),
            "vod_pic": raw_item.get("vod_pic", ""),
            "type_name": raw_item.get("type_name", ""),
            "vod_remarks": raw_item.get("vod_remarks", "")
        }

    @staticmethod
    def filter_base_list(raw_list: List[Dict]) -> List[Dict]:
        return [VideoCollector.filter_base_fields(item) for item in raw_list]

    @staticmethod
    def filter_detail_fields(raw_item: Dict) -> Dict:
        return {
            "vod_name": raw_item.get("vod_name", ""),
            "vod_pic": raw_item.get("vod_pic", ""),
            "type_name": raw_item.get("type_name", ""),
            "vod_remarks": raw_item.get("vod_remarks", ""),
            "vod_year": raw_item.get("vod_year", ""),
            "vod_area": raw_item.get("vod_area", ""),
            "vod_lang": raw_item.get("vod_lang", ""),
            "vod_director": raw_item.get("vod_director", ""),
            "vod_actor": raw_item.get("vod_actor", ""),
            "vod_score": raw_item.get("vod_score", ""),
            "vod_time": raw_item.get("vod_time", ""),
            "vod_content": raw_item.get("vod_content", ""),
            "vod_play_from": raw_item.get("vod_play_from", ""),
            "vod_play_url": raw_item.get("vod_play_url", "")
        }

    @staticmethod
    def filter_detail_list(raw_list: List[Dict]) -> List[Dict]:
        return [VideoCollector.filter_detail_fields(item) for item in raw_list]

    @staticmethod
    def redis_set(key: str, data: Dict):
        json_str = json.dumps(data, ensure_ascii=False)
        # redis_client.set(key, json_str)
        redis_client.set_ex(key, json_str, ex=7776000)

    @staticmethod
    def redis_get(key: str) -> Dict | None:
        data_str = redis_client.get(key)
        if not data_str:
            return None
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None

    async def collect_all_videos(self, task_status, sp: str, is_full: bool = False):
        site_config = config_manager.get_vod_config(sp)
        if not site_config:
            logger.error(f"未找到 sp={sp} 的站点配置")
            task_status.update({"processed": 0, "progress": 100, "updated_at": int(time.time())})
            return {"fail": 0, "success": 0, "skipped": 0}

        total = task_status["total"]
        success = failed = skipped = processed = 0

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            for cat_name, video_names in site_config.site_videos.items():
                for video_name in video_names:
                    processed += 1
                    redis_key = f"tv-vod:{sp}:{cat_name}:{video_name}"
                    if not is_full and self.redis_get(redis_key):
                        skipped += 1
                        continue

                    video_data = await self._collect_detail(client, video_name, site_config)
                    if video_data:
                        self.redis_set(redis_key, video_data)
                        success += 1
                        logger.debug(f"[{sp}] 采集成功：{cat_name}/{video_name}")
                    else:
                        failed += 1
                        logger.warning(f"[{sp}] 采集失败：{cat_name}/{video_name}")

                    task_status.update({
                        "processed": processed,
                        "progress": round(processed / total * 100, 2),
                        "success": success,
                        "updated_at": int(time.time()),
                    })

        # 最终状态
        task_status.update({
            "processed": processed,
            "progress": round(processed / total * 100, 2),
            "success": success,
            "updated_at": int(time.time()),
        })
        return {"fail": failed, "success": success, "skipped": skipped}

    async def _collect_detail(self, client: httpx.AsyncClient, video_name: str, site_config):
        for site in site_config.site_collections:
            try:
                params = {"ac": "detail", "wd": video_name}
                url = f"{site.url}?{urlencode(params)}"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data and len(data.get("list", [])) > 0:
                    data_list = self.filter_detail_list(data["list"])
                    for video in data_list:
                        if video.get("vod_name") == video_name:
                            site.repair_pic_url("vod_pic", video)
                            return video
            except Exception as e:
                continue
        return None
