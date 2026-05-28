import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, override, List, Optional

import httpx

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider
from services.spider.factory import register_spider

logger = LoggerFactory.get_logger(__name__)

MAX_VIDEO_NUM = 8


@register_spider("v-youtub")
class YoutubSpider(BaseSpider):
    _header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com"
    }
    _deno_available = False
    _deno_bin_dir = None

    def _get_base_url(self) -> str:
        return self.config.site_collections[0].url

    def _get_api_key(self) -> str:
        return self.config.site_collections[0].key

    def _ensure_deno(self, env: dict) -> bool:
        """确保 Deno 可用（高性能缓存版）"""
        if self._deno_available:
            if self._deno_bin_dir:
                current_path = env.get("PATH", "")
                if self._deno_bin_dir not in current_path.split(os.pathsep):
                    env["PATH"] = self._deno_bin_dir + os.pathsep + current_path
            return True

        deno_path = shutil.which("deno", path=env.get("PATH"))
        if deno_path:
            self._deno_available = True
            self._deno_bin_dir = None
            logger.debug("[YouTube] Deno 已在 PATH 中")
            return True

        possible_paths = [
            "/usr/local/bin",
            os.path.expanduser("~/.deno/bin"),
            "/root/.deno/bin",
        ]
        for p in possible_paths:
            deno_bin = os.path.join(p, "deno")
            if os.path.isfile(deno_bin) and os.access(deno_bin, os.X_OK):
                self._deno_available = True
                self._deno_bin_dir = p
                env["PATH"] = p + os.pathsep + env.get("PATH", "")
                logger.debug(f"[YouTube] Deno 位于 {p}，已加入 PATH")
                return True

        logger.error("[YouTube] ❌ 未找到 Deno 运行时！请安装 Deno 或设置正确的 PATH")
        self._deno_available = False
        return False

    def _sync_parse(self, url: str, cookie_path: str, proxy: Optional[str]) -> Optional[str]:
        """同步解析逻辑（优化版：保留 Deno 检查，超时降至 20s，日志精简）"""
        env = os.environ.copy()
        if not self._ensure_deno(env):
            return None

        cmd = [
            sys.executable,
            "-m", "yt_dlp", "-v", "-j",
            "--cookies", cookie_path,
            "--remote-components", "ejs:npm",
            "--no-playlist",
            "--socket-timeout", "20",
            url
        ]
        if proxy:
            cmd.extend(["--proxy", proxy])
        logger.debug(f"[YouTube] 执行命令: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )

            # 记录 stderr 前 500 字符（便于排错）
            if proc.stderr:
                err_head = proc.stderr.strip()[:500]
                logger.debug(f"[YouTube] yt-dlp stderr 头部:\n{err_head}")

            if proc.returncode != 0:
                logger.warning(f"[YouTube] yt-dlp 执行失败，返回码 {proc.returncode}")
                return None

            info = json.loads(proc.stdout)
            return self._select_best_url(info, id=url.split("=")[-1], min_h=360, max_h=720)

        except subprocess.TimeoutExpired:
            logger.warning("[YouTube] yt-dlp 执行超时（20秒）")
        except json.JSONDecodeError as e:
            logger.warning(f"[YouTube] JSON 解析失败: {e}")
        except Exception as e:
            logger.warning(f"[YouTube] 命令行异常: {e}")

        return None

    def _select_best_url(self, info: dict, id: str = "", min_h: int = 360, max_h: int = 720) -> Optional[str]:
        """优化：增加 protocol 过滤，使用生成器减少内存"""
        formats = info.get("formats") or []

        def is_video(f):
            return (
                    f.get("url")
                    and f.get("vcodec") != "none"
                    and f.get("height", 0) > 0
                    and f.get("protocol") not in ("mhtml", "http_dash_segments")
                    and not f["url"].split("?")[0].endswith((".jpg", ".png", ".webp"))
            )

        # 1. progressive (有音频)
        progressive = [
            f for f in formats
            if is_video(f) and f.get("acodec") != "none" and min_h <= f["height"] <= max_h
        ]
        if progressive:
            best = max(progressive, key=lambda x: x["height"])
            logger.info(f"[YouTube] 选择 progressive {best['height']}p: {id}")
            return best["url"]

        # 2. video only
        video_only = [
            f for f in formats
            if is_video(f) and f.get("acodec") == "none" and min_h <= f["height"] <= max_h
        ]
        if video_only:
            best = max(video_only, key=lambda x: x["height"])
            logger.info(f"[YouTube] 选择 video only {best['height']}p: {id}")
            return best["url"]

        # 3. 降级
        all_video = [f for f in formats if is_video(f)]
        if all_video:
            below = [f for f in all_video if f["height"] < min_h]
            if below:
                fallback = max(below, key=lambda x: x["height"])
                logger.debug(f"[YouTube] 降至 {fallback['height']}p (低于{min_h}p)")
                return fallback["url"]
            above = [f for f in all_video if f["height"] > max_h]
            if above:
                fallback = min(above, key=lambda x: x["height"])
                logger.debug(f"[YouTube] 降至 {fallback['height']}p (高于{max_h}p)")
                return fallback["url"]

        return info.get("url") or (info.get("requested_formats", [{}])[0].get("url"))

    @override
    async def get_list_data(self, t: str, pg: int) -> Dict:
        cat_name = self.config.get_site_cate_name(t)
        cat_data_list = self.redis_dir_data(cat_name)
        data = []
        for key, value in cat_data_list.items():
            filted_data = self.filter_base_fields(value)
            video_data = {"vod_id": f"{cat_name}/{key}", **filted_data}
            data.append(video_data)
        return self.paginate_list(data, pg)

    @override
    async def get_player(self, id: str) -> Optional[str]:
        """解析 YouTube 视频，返回 360~720p 的可播放直链"""
        proxy = self._service.vpn_proxy
        cookie_path = self._service.cookie_file
        try:
            if not cookie_path or not os.path.exists(cookie_path):
                logger.error(f"[YouTube] cookie 文件不存在: {cookie_path}")
                return None

            url = f"https://www.youtube.com/watch?v={id}"
            loop = asyncio.get_event_loop()

            stream_url = await loop.run_in_executor(
                None, self._sync_parse, url, cookie_path, proxy
            )
            if stream_url:
                return stream_url
            logger.warning(f"[YouTube] 未获取到可用流: {id}")

        except Exception as e:
            err = str(e)
            if "Sign in" in err or "bot" in err:
                logger.error(f"[YouTube] Cookie 已过期: {cookie_path}")
            elif "Private video" in err:
                logger.error(f"[YouTube] 私有视频: {id}")
            elif "Video unavailable" in err:
                logger.error(f"[YouTube] 视频不可用: {id}")
            else:
                logger.error(f"[YouTube] 解析错误 {id}: {err}")

        return None

    @override
    def get_player_json(self, parse, id, url):
        return {"id": id, "parse": parse, "url": url, "header": self._header}

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
                        self.redis_set(redis_key, video_data, ex=2 * 86400)

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
                video_play_url = f"{self._service.url_parse}".replace("{sp}", self._sp).replace("{id}", video_id)
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
                    "vod_play_from": "Youtube直连",
                    "vod_play_url": f"播放${video_play_url}"
                })
            return videos
        except Exception as e:
            logger.error(f"获取频道 {channel_id} 数据失败: {str(e)}")
            return []
