import time
from typing import Dict, override
from urllib.parse import urlencode

import httpx

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider, headers
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)

MAX_VIDEO_NUM = 8


@register_spider("v-newx")
class NewXSpider(BaseSpider):
    _header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
    }

    def _process_cate_detail(self, item: Dict, site_url) -> Dict:
        return {
            "vod_id": item.get("url", "").replace(f"{site_url}?xvid=", ""),
            "vod_name": item.get("title", "").replace("AVOTC资源网——", ""),
            "vod_pic": item.get("img", ""),
            "vod_remarks": item.get("time", ""),
        }

    def _process_video_detail(self, vid: str, item: Dict) -> Dict:
        return {
            "vod_id": vid,
            "vod_name": item.get("title", ""),
            "vod_pic": item.get("ThumbUrl", ""),
            "vod_play_from": "XVIDEOS直连",
            "vod_play_url": f"播放${item.get("hls", "")}",
        }

    @override
    async def get_list_data(self, t: str, pg: int) -> Dict:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            videos = []
            for site in self.config.site_collections:
                try:
                    params = {"play": "class", "c": t}
                    url = f"{site.url}?{urlencode(params)}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data and len(data) > 0:
                        for item in data:
                            videos.append(self._process_cate_detail(item, site.url))
                except Exception as e:
                    continue
        return self.paginate_list(videos, pg)

    @override
    async def get_detail_data(self, ids: str) -> Dict:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            data = None
            for site in self.config.site_collections:
                try:
                    params = {"xvid": ids}
                    url = f"{site.url}?{urlencode(params)}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    if resp_json:
                        data = self._process_video_detail(ids, resp_json)
                        break
                except Exception as e:
                    continue
        return {"list": [data] if data else []}

    @override
    async def search_data(self, keyword: str, pg: int) -> Dict:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            videos = []
            for site in self.config.site_collections:
                try:
                    params = {"play": "k", "k": keyword}
                    url = f"{site.url}?{urlencode(params)}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    if data and len(data) > 0:
                        for item in data:
                            videos.append(self._process_cate_detail(item, site.url))
                except Exception as e:
                    continue
        return self.paginate_list(videos, pg)

    async def collect(self, task_info: Dict, is_full: bool = False) -> Dict:
        total = task_info["total"]
        success = failed = skipped = processed = total  # 0

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            pass
            # for site_c in self.config.site_class:
            #     cat_id = site_c["type_id"]
            #     cat_name = site_c["type_name"]
            #     processed += 1
            #     # redis_key = self.make_redis_key(cat_name, cat_id)
            #     # if not is_full and self.redis_get(redis_key):
            #     #     skipped += 1
            #     #     continue
            #
            #     video_datas = await self._collect_videos(client, cat_id, cat_name, self.config)
            #     for video in video_datas:
            #         redis_key = self.make_redis_key(cat_id, video["vod_key"])
            #         # if not is_full and self.redis_get(redis_key):
            #         #     skipped += 1
            #         #     continue
            #
            #     if video_datas:
            #         self.redis_set(redis_key, video_data)
            #         success += 1
            #         logger.debug(f"[{self._sp}] 采集成功：{cat_name}/{video_name}")
            #     else:
            #         failed += 1
            #         logger.warning(f"[{self._sp}] 采集失败：{cat_name}/{video_name}")
            #
            #     task_info.update({
            #         "processed": processed,
            #         "progress": round(processed / total * 100, 2),
            #         "success": success,
            #         "updated_at": int(time.time()),
            #     })

        # 最终状态
        task_info.update({
            "processed": processed,
            "progress": round(processed / total * 100, 2),
            "success": success,
            "updated_at": int(time.time()),
        })
        return {"fail": failed, "success": success, "skipped": skipped}
