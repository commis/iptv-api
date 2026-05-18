import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, override

import feedparser
import httpx
import yt_dlp

from core.logger_factory import LoggerFactory
from services import config_manager
from services.spider.base import BaseSpider
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)

ONE_WEEK_AGO = datetime.now() - timedelta(days=15)


@register_spider("v-youtub")
class YoutubSpider(BaseSpider):

    def _get_base_url(self) -> str:
        return self.config.site_collections[0].url

    @override
    def get_list_data(self, t: str, pg: int) -> Dict:
        cat_name = self.config.get_site_cate_name(t)
        cat_data_list = self.redis_dir_data(cat_name)
        data = []
        for key, value in cat_data_list.items():
            filted_data = self.filter_base_fields(value)
            video_data = {"vod_id": f"{cat_name}/{key}", **filted_data}
            data.append(video_data)
        return self.paginate_list(data, pg)

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
                        if not is_full and self.redis_exists(redis_key):
                            continue
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
                    "vod_area": "未知",
                    "vod_lang": "国语",
                    "vod_director": entry.author,
                    "vod_actor": entry.author,
                    "vod_score": "0.0",
                    "vod_time": f"{published_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "vod_content": entry.get("summary", "")[:200],
                    "vod_play_from": "YouTube",
                    "vod_play_url": f"{config_manager.service_params.url_parse}{entry.link}"
                })
            return videos
        except Exception as e:
            logger.error(f"获取频道 {channel_id} 视频失败: {str(e)}")
            return []

    @staticmethod
    def resolve(url: str) -> str:
        serv_params = config_manager.service_params
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "format": "best",
            "proxy": serv_params.vpn_proxy,
            "cookiefile": serv_params.cookie_file,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            merged = [
                f for f in formats
                if f.get("url") and f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")
            ]

            if not merged:
                raise ValueError("未找到可直接播放的合并流")

            merged.sort(key=lambda f: f.get("height") or 0, reverse=True)
            best = merged[0]
            return best["url"]
