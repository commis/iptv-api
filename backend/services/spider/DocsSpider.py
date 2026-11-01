import time
from typing import Dict
from urllib.parse import urlencode

import httpx

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider, headers
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)


@register_spider("v-docs")
class DocsSpider(BaseSpider):

    async def collect(self, task_info: Dict, is_full: bool = False) -> Dict:
        total = task_info["total"]
        success = failed = skipped = processed = 0

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            for cat_name, video_names in self.config.site_videos.items():
                for video_name in video_names:
                    processed += 1
                    redis_key = self.make_redis_key(cat_name, video_name)
                    if not is_full and self.redis_get(redis_key):
                        skipped += 1
                        continue

                    video_data = await self._collect_detail(client, video_name, self.config)
                    if video_data:
                        self.redis_set(redis_key, video_data)
                        success += 1
                        logger.debug(f"[{self._sp}] 采集成功：{cat_name}/{video_name}")
                    else:
                        failed += 1
                        logger.warning(f"[{self._sp}] 采集失败：{cat_name}/{video_name}")

                    task_info.update({
                        "processed": processed,
                        "progress": round(processed / total * 100, 2),
                        "success": success,
                        "updated_at": int(time.time()),
                    })

        # 最终状态
        task_info.update({
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
