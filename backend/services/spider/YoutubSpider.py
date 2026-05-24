import asyncio
import random
import re
import time
from datetime import datetime
from typing import Dict, override, List, Any

import httpx

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)

MAX_VIDEO_NUM = 10


@register_spider("v-youtub")
class YoutubSpider(BaseSpider):
    _header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0,gzip(gfe)",
        "Accept-Language": "zh,en-US;q\u003d0.9"
    }

    def _get_base_url(self) -> str:
        return self.config.site_collections[0].url

    def _get_api_key(self) -> str:
        return self.config.site_collections[0].key

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

    @override
    async def get_player(self, vid: str) -> str | None:
        proxy = self._service.vpn_proxy
        try:
            import os, yt_dlp
            cookie_path = self._service.cookie_file
            if not cookie_path or not os.path.exists(cookie_path):
                logger.error(f"[YouTube] cookie 文件不存在: {cookie_path}")
                return None

            url = f"https://www.youtube.com/watch?v={vid}"
            loop = asyncio.get_event_loop()

            def run_parse():
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "cookiefile": cookie_path,
                    "proxy": proxy or None,
                    "http_headers": self._header,
                    "noplaylist": True,
                    "extractor_args": {"youtube": {"player_client": ["web"]}},
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False, process=False)

                if not info:
                    return None

                formats = info.get("formats") or []

                # 1. 优先：有声有画的 mp4（progressive，无需 ffmpeg）
                progressive = [
                    f for f in formats
                    if (f.get("url")
                        and f.get("ext") == "mp4"
                        and f.get("vcodec", "none") != "none"
                        and f.get("acodec", "none") != "none")
                ]
                if progressive:
                    return max(progressive, key=lambda f: f.get("height") or 0)["url"]

                # 2. 降级：有画面的任意格式
                video_only = [
                    f for f in formats
                    if f.get("url") and f.get("vcodec", "none") != "none"
                ]
                if video_only:
                    return max(video_only, key=lambda f: f.get("height") or 0)["url"]

                # 3. 兜底：第一个有 url 的
                for f in formats:
                    if f.get("url"):
                        return f["url"]

                return None

            stream_url = await loop.run_in_executor(None, run_parse)
            if stream_url:
                return stream_url
            else:
                logger.warning(f"[YouTube] 未获取到可用流: {vid}")
        except Exception as e:
            err = str(e)
            if "Sign in" in err or "bot" in err:
                logger.error(f"[YouTube] Cookie 已过期，请重新导出: {self._service.cookie_file}")
            elif "Private video" in err:
                logger.error(f"[YouTube] 私有视频: {vid}")
            elif "Video unavailable" in err:
                logger.error(f"[YouTube] 视频不可用: {vid}")
            else:
                logger.error(f"[YouTube] 解析错误 {vid}: {err}")

        return None

    @override
    def get_player_json(self, parse, url):
        return {"parse": parse, "url": url, "header": self._header}

    async def collect(self, task_info: Dict, is_full: bool = False) -> Dict:
        total = task_info["total"]
        success = failed = skipped = processed = 0

        async with httpx.AsyncClient(timeout=20) as client:
            for cat_name, channel_list in self.config.site_videos.items():
                for uname in channel_list:
                    processed += 1
                    channel_user, channel_id = await self._get_channel_id(client, uname)
                    if not channel_id:
                        failed += 1
                        continue

                    time.sleep(random.uniform(1.5, 3))
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
            match_id = re.search(r'\?channel_id=(UC[0-9A-Za-z_-]{22})\"', resp.text)
            if match_id:
                return channel_name.strip(), match_id.group(1)
            else:
                return channel_name.strip(), ""
        except Exception as e:
            logger.error(f"获取频道ID失败：{channel_value}，错误：{str(e)}")
            return channel_name.strip(), ""

    async def _get_recent_videos(self, client: httpx.AsyncClient, channel_user: str, channel_id: str) -> List[Dict]:
        videos = []
        rss_url = (f"https://www.googleapis.com/youtube/v3/search?channelId={channel_id}"
                   f"&part=snippet&maxResults={MAX_VIDEO_NUM}&order=date&type=video&key={self._get_api_key()}")
        try:
            resp = await client.get(rss_url, headers=self._header, follow_redirects=True, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                author = snippet["channelTitle"]
                published_str = snippet["publishedAt"]
                published_time = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                video_play_url = f"{self._service.url_parse}".replace("{sp}", self._sp).replace("{vid}", video_id)
                # video_play_url = f"{self._get_base_url()}/embed/{video_id}?autoplay=1"
                videos.append({
                    "vod_key": video_id,
                    "vod_name": snippet["title"],
                    "vod_pic": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    "type_name": channel_user,
                    "vod_remarks": f"{published_time.strftime('%m-%d %H:%M')}",
                    "vod_year": f"{published_time.strftime('%Y')}",
                    "vod_director": author,
                    "vod_time": f"{published_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "vod_content": snippet["description"][:200],
                    "vod_play_from": "Youtube",
                    "vod_play_url": f"播放${video_play_url}"
                })
            return videos
        except Exception as e:
            logger.error(f"获取频道 {channel_id} 数据失败: {str(e)}")
            return []
