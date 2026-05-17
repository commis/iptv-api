import re
import time
from datetime import datetime, timedelta
from typing import Dict, List

import feedparser
import httpx

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)

ONE_WEEK_AGO = datetime.now() - timedelta(days=15)


@register_spider("v-youtub")
class YoutubSpider(BaseSpider):

    def _get_base_url(self) -> str:
        return self.config.site_collections[0].url

    async def collect(self, task_info: Dict, is_full: bool = False) -> Dict:
        total = task_info["total"]
        success = failed = skipped = processed = 0

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            for cat_name, channel_list in self.config.site_videos.items():
                for uname in channel_list:
                    processed += 1
                    channel_user, channel_id = await self._get_channel_id(client, uname)
                    if not channel_id:
                        failed += 1
                        continue

                    videos = await self._get_recent_videos(client, channel_user, channel_id)
                    for v in videos:
                        video_name = v.get("vod_key")
                        video_data = self.filter_detail_fields(v)
                        redis_key = self.make_redis_key(cat_name, video_name)
                        self.redis_set(redis_key, video_data, ex=10 * 86400)

                    success += 1
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

    async def _get_channel_id(self, client: httpx.AsyncClient, handle: str) -> tuple[str, str]:
        match = re.search(r'(.*)[:：](.*)', handle)
        channel_name, channel_value = match.groups() if match else ("", handle.strip())
        if channel_value.startswith("UC"):
            return channel_name.strip(), channel_value.strip()

        try:
            url = f"{self._get_base_url()}/{channel_value}"
            resp = await client.get(url, follow_redirects=True, timeout=10)
            resp.raise_for_status()
            match_id = re.search(r'channel_id=(UC[0-9A-Za-z_-]{22})', resp.text)
            if match_id:
                return channel_name.strip(), match_id.group(1)
            else:
                return channel_name.strip(), ""
        except Exception as e:
            logger.error(f"获取频道ID失败：{channel_value}，错误：{str(e)}")
            return channel_name.strip(), ""

    async def _get_recent_videos(self, client: httpx.AsyncClient, channel_user: str, channel_id: str) -> List[Dict]:
        videos = []
        rss_url = f"{self._get_base_url()}/feeds/videos.xml?channel_id={channel_id}"
        try:
            resp = await client.get(rss_url, follow_redirects=True, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                published_time = datetime(*entry.published_parsed[:6])
                if published_time < ONE_WEEK_AGO:
                    continue
                videos.append({
                    "vod_key": entry.yt_videoid,
                    "vod_name": entry.title,
                    "vod_pic": f"https://i.ytimg.com/vi/{entry.yt_videoid}/hqdefault.jpg",
                    "type_name": channel_user,
                    "vod_remarks": f"{published_time.strftime('%Y-%m-%d %H:%M')}",
                    "vod_year": f"{published_time.strftime('%Y')}",
                    "vod_area": "",
                    "vod_lang": "",
                    "vod_director": entry.author,
                    "vod_actor": entry.author,
                    "vod_score": "0.0",
                    "vod_time": f"{published_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "vod_content": entry.get("summary", "")[:200],
                    "vod_play_from": "YouTube",
                    "vod_play_url": entry.link
                })
            return videos
        except Exception as e:
            logger.error(f"获取频道 {channel_id} 视频失败: {str(e)}")
            return []
