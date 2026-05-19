import abc
import json
from typing import Dict, Optional, List
from urllib.parse import unquote

from core.logger_factory import LoggerFactory
from services import config_manager
from services.redis import redis_client

logger = LoggerFactory.get_logger(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}


class BaseSpider(abc.ABC):
    """抽象爬虫基类：所有爬虫必须实现以下方法"""

    def __init__(self, sp: str):
        self._sp = sp
        self._config = config_manager.get_vod_config(sp)

    @property
    def config(self):
        return self._config

    # ------------------------------
    # 必须实现的抽象方法
    # ------------------------------
    # @abc.abstractmethod
    def get_list_data(self, t: str, pg: int) -> Dict:
        """获取列表数据（ac=detail & t=分类ID 时调用）"""
        cat_name = self.config.get_site_cate_name(t)
        videos = self.config.site_videos.get(cat_name, [])
        data = [self.get_video_base_from_redis(cat_name, name) for name in videos]
        return self.paginate_list(data, pg)

    # @abc.abstractmethod
    def get_detail_data(self, ids: str) -> Dict:
        """获取详情数据（ac=detail & ids=cat/name 时调用）"""
        try:
            cat_name, video_name = unquote(ids).split("/", 1)
            cache = self.get_video_detail_from_redis(cat_name, video_name)
            return {"list": [cache] if cache else []}
        except ValueError:
            logger.error(f"ids格式错误: {ids}，正确格式为 分类/文件名")
            return {"list": []}

    # @abc.abstractmethod
    def search_data(self, keyword: str, pg: int) -> Dict:
        """搜索数据（wd=关键词 时调用）"""
        res = [
            self.get_video_base_from_redis(cat, name)
            for cat, videos in self.config.site_videos.items()
            for name in videos
            if keyword in name
        ]
        return self.paginate_list(res, pg)

    @abc.abstractmethod
    def player_content(self, flag: str, pid: str, vipFlags: str) -> Dict:
        """播放视频（player配置后调用）"""
        pass

    @abc.abstractmethod
    async def collect(self, task_info: Dict, is_full: bool = False) -> Dict:
        """采集数据（后台任务调用）"""
        pass

    # ------------------------------
    # 通用工具方法（所有爬虫复用）
    # ------------------------------
    def make_redis_key(self, *parts) -> str:
        return f"tv-vod:{self._sp}:{':'.join(parts)}"

    def redis_exists(self, key: str):
        return redis_client.exists(key)

    def redis_set(self, key: str, data: dict, ex: int = 90 * 86400):
        redis_client.set_ex(key, json.dumps(data, ensure_ascii=False), ex)

    def redis_get(self, key: str) -> Optional[dict]:
        val = redis_client.get(key)
        return json.loads(val) if val else None

    def redis_dir_data(self, prefix: str) -> Dict:
        """
        获取 Redis 指定目录下所有 key 对应的 value
        :return: {key: value} 字典
        """
        pattern = f"tv-vod:{self._sp}:{prefix}*"
        keys = redis_client.prefix_keys(pattern)
        result = {}

        for key in keys:
            val = self.redis_get(key)
            if val:
                key_str = key.replace(pattern.replace("*", ":"), "")
                result[key_str] = val

        return result

    # ------------------------------
    # 视频采集或查询处理的通用方法（所有爬虫复用）
    # ------------------------------
    def filter_base_fields(self, raw_item: Dict) -> Dict:
        return {
            "vod_name": raw_item.get("vod_name", ""),
            "vod_pic": raw_item.get("vod_pic", ""),
            "type_name": raw_item.get("type_name", ""),
            "vod_remarks": raw_item.get("vod_remarks", "")
        }

    def filter_base_list(self, raw_list: List[Dict]) -> List[Dict]:
        return [self.filter_base_fields(item) for item in raw_list]

    def filter_detail_fields(self, raw_item: Dict) -> Dict:
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

    def filter_detail_list(self, raw_list: List[Dict]) -> List[Dict]:
        return [self.filter_detail_fields(item) for item in raw_list]

    def paginate_list(self, data_list: List[Dict], page: int, page_size: int = 20) -> Dict:
        total = len(data_list)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = data_list[start:end]
        return {
            "list": page_data,
            "total": total,
            "page": page
        }

    def get_video_detail_from_redis(self, cat_name: str, video_name: str) -> Dict | None:
        define_id = f"{cat_name}/{video_name}"
        redis_key = self.make_redis_key(cat_name, video_name)
        redis_data = self.redis_get(redis_key)
        if redis_data:
            video_data = {"vod_id": define_id, **redis_data}
            return video_data

        return {
            "vod_id": f"{define_id}",
            "vod_name": video_name,
            "vod_pic": self.config.site_video_cover,
            "type_name": cat_name,
            "vod_remarks": "未采集",
        }

    def get_video_base_from_redis(self, cat_name: str, video_name: str) -> Dict | None:
        define_id = f"{cat_name}/{video_name}"
        redis_key = self.make_redis_key(cat_name, video_name)
        redis_data = self.redis_get(redis_key)
        if redis_data:
            field_result = self.filter_base_fields(redis_data)
            video_data = {"vod_id": define_id, **field_result}
            return video_data

        return {
            "vod_id": f"{define_id}",
            "vod_name": video_name,
            "vod_pic": self.config.site_video_cover,
            "type_name": cat_name,
            "vod_remarks": "未采集",
        }
