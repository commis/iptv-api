import glob
import logging
import os
import re
import threading
from typing import Dict, Optional, Any, List

import yaml

from core.logger_factory import LoggerFactory
from core.singleton import singleton

logger = LoggerFactory.get_logger(__name__, level=logging.INFO)


class CollectInfo:

    def __init__(self, collect_data: Dict[str, Any]):
        self._url: str = collect_data["url"]
        self._key: str = collect_data.get("key", "")
        self._pic: Dict[str, Any] = collect_data.get("pic", {})

    @property
    def url(self):
        return self._url

    @property
    def key(self):
        return self._key

    def repair_pic_url(self, key: str, data: Dict[str, Any]):
        if self._pic:
            value = data[key]
            data[key] = value.replace(self._pic["from"], self._pic["to"])


class SiteVideoConfig:
    """
    点播原的相关配置信息
    """

    def __init__(self, config_data: Dict[str, Any]):
        self._default_cover = config_data.get("default_cover", "")

        self._site_collects: List[CollectInfo] = []
        self._site_class: List[Dict] = []
        self._site_videos: Dict[str, List[str]] = {}
        self._video_total = 0

        collect_list = config_data.get("collect_sites", [])
        for key in collect_list:
            self._site_collects.append(CollectInfo(collect_list[key]))

        class_config = config_data.get("class", {})
        for idx, (cat_name, data) in enumerate(class_config.items(), start=1):
            episodes = data.get("episodes", [])
            self._site_class.append({"type_id": str(idx), "type_name": cat_name})
            self._site_videos[cat_name] = episodes
            self._video_total += len(episodes)

    @property
    def site_video_cover(self):
        return self._default_cover

    @property
    def video_total(self):
        return self._video_total if self._video_total > 0 else 1

    @property
    def site_class(self):
        return self._site_class

    @property
    def site_collections(self):
        return self._site_collects

    @property
    def site_videos(self):
        return self._site_videos

    def get_site_cate_name(self, tid: str | str) -> str | None:
        for c in self._site_class:
            if c["type_id"] == tid:
                return c["type_name"]
        return None


class ServParams:

    def __init__(self, config_data: Dict[str, Any]):
        self._log_level = config_data.get("log_level", "info")
        self._url_parse = config_data.get("url_parse", "")
        self._vpn_proxy = config_data.get("vpn_proxy", "")
        self._cookie_file = config_data.get("cookie_file", "")

    @property
    def log_level(self) -> str:
        return self._log_level

    @property
    def url_parse(self) -> str:
        return self._url_parse

    @property
    def vpn_proxy(self) -> str:
        return self._vpn_proxy

    @property
    def cookie_file(self) -> str:
        return self._cookie_file


@singleton
class ConfigManager:
    """
    管理分类与图标映射关系的单例类
    """

    _vod_config_map: Dict[str, SiteVideoConfig] = {}
    _channel_relations_fix: Dict[str, Dict[str, object]] = {}
    _chanbel_compiled_patterns = []

    def __init__(self):
        self._lock = threading.RLock()
        service_config_path = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../../spider/dist/conf",
                "service.yaml",
            )
        )
        full_config = self._load_config(service_config_path)
        self._service_params = ServParams(full_config.get("service", {}))
        self._redis_config: Dict[str, Any] = full_config["redis_cache"]
        self._category_map: Dict[str, str] = full_config["category_map"]
        self._ignore_categories: Dict[str, str] = full_config["ignore_category"]
        self._channel_id_map: Dict[str, str] = full_config["channel_id_map"]
        self._channel_name_map: Dict[str, str] = full_config["channel_name_map"]
        self._categories: Dict[str, Dict[str, Any]] = full_config["channel_map"]
        self._init_channel_relations()
        del full_config

        self._init_vod_configs()

    @property
    def service_params(self) -> ServParams:
        return self._service_params

    @property
    def redis_config(self):
        return self._redis_config

    def get_vod_config(self, key: str):
        return self._vod_config_map.get(key, None)

    def _load_config(self, config_path) -> Dict[str, Any]:
        """加载完整配置（仅临时使用）"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"the config is not exist, file：{config_path}\n"
                f"Please check spider/service.yaml file"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # 校验核心节点
            required = [
                "category_map",
                "ignore_category",
                "channel_map",
                "channel_id_map",
                "channel_name_map",
            ]
            missing = [n for n in required if n not in config_data]
            if missing:
                raise ValueError(f"failed to load config：{missing}")

            return config_data
        except yaml.YAMLError as e:
            raise RuntimeError(f"failed to parse yaml：{str(e)}")
        except Exception as e:
            raise RuntimeError(f"load yaml exception：{str(e)}")

    def _init_channel_relations(self):
        """初始化频道名称与分类的映射关系"""
        pattern = r'[.*+?^$()\[\]{}|\\]'
        with self._lock:
            for category_name, category_info in self._categories.items():
                category_info.update({"name": category_name})
                category_info.update({"excludes": category_info.get("excludes", [])})
                channel_list = category_info.get("channels", [])
                for channel in channel_list:
                    if bool(re.search(pattern, channel)):
                        regex_str = channel.replace("*", ".*")
                        self._chanbel_compiled_patterns.append((re.compile(regex_str), category_info))
                    else:
                        self._channel_relations_fix[channel] = category_info

    def _init_vod_configs(self):
        conf_dir = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../spider/dist/conf"))
        yaml_pattern = os.path.join(conf_dir, "v-*.yaml")
        config_files = glob.glob(yaml_pattern)

        for file_path in config_files:
            if not os.path.isfile(file_path):
                continue

            config_key = os.path.splitext(os.path.basename(file_path))[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                    config_object = SiteVideoConfig(config_data)
                    self._vod_config_map[config_key] = config_object
            except yaml.YAMLError as e:
                logger.error(f"failed to parse yaml：{str(e)}")
            except Exception as e:
                logger.error(f"load yaml exception：{str(e)}")

    def is_ignore(self, category: str):
        """判断是否为忽略的分类"""
        return category in self._ignore_categories

    def is_exclude(self, category_info: {}, channel_name: str) -> bool:
        """
        判断是否为排除的频道
        支持三种匹配规则（可混合在excludes列表中，优先级同等）：
        1. 精准全文匹配（原逻辑）：如 "浙江卫视" → 只有频道名完全相等才命中
        2. 通配符匹配（你的需求）：如 "*超清"、"体育*"、"*央视*" → 最常用
        3. 原生正则表达式：如 r"^\\d+频道$"、r"超清|高清|蓝光" → 复杂场景适配
        核心优先级（不变）：白名单channels > 所有排除规则，在白名单的频道永不排除
        """
        channels = category_info.get("channels", [])
        excludes = category_info.get("excludes", [])

        # 先判断是否命中【精准全文匹配】- 原逻辑保留
        if channel_name in excludes:
            return channel_name not in channels

        # 遍历匹配【通配符/原生正则表达式】规则
        for pattern in excludes:
            regex_pattern = pattern.replace("*", ".*")
            if re.fullmatch(regex_pattern, channel_name, flags=re.IGNORECASE):
                return channel_name not in channels

        # 未命中任何排除规则
        return False

    def get_groups(self):
        """获取所有分类的组"""
        with self._lock:
            return self._categories.keys()

    def exists(self, category: str) -> bool:
        """
        判断指定分类是否存在
        """
        with self._lock:
            return category in self._categories

    def do_channel_logo(self, category: str) -> int:
        """
        分类是否需要替换logo路经，使用二进制位表示，显示不替换
        00=0: 关闭， 01=1：显示
        """
        default_value: int = 1
        with self._lock:
            cagegory_info = self._categories.get(category)
            if cagegory_info:
                return int(cagegory_info.get("tvg_logo", default_value))
        return default_value

    def get_category_info(self, category_name: str) -> Optional[Dict[str, object]]:
        """
        获取指定分类的图标
        """
        with self._lock:
            return self._categories.get(category_name)

    def get_category_object(self, channel_name: str, category_name):
        """
        根据频道名称获取分类名称
        """
        if channel_name in self._channel_relations_fix:
            return self._channel_relations_fix[channel_name]

        # 模糊匹配
        for regex_obj, value in self._chanbel_compiled_patterns:
            if regex_obj.fullmatch(channel_name):
                return value

        # 没有对应的分类时，构造储一个新的分类
        target_info = self._categories.get(category_name)
        return target_info if target_info else self._categories.get("其他收藏")

    def update_category(self, category_infos: Dict[str, Dict[str, object]]) -> None:
        """
        更新分类图标映射
        """
        with self._lock:
            self._categories.update(category_infos)

    def remove_category(self, category_name: str) -> None:
        """
        移除指定分类的图标映射
        """
        with self._lock:
            self._categories.pop(category_name, None)

    def list_categories(self) -> Dict[str, object]:
        """获取所有分类图标映射的副本"""
        with self._lock:
            return self._categories.copy()

    def get_category(self, category_name: str) -> str:
        return self._category_map.get(category_name, category_name)

    def get_channel(self, channel_name: str) -> str:
        pattern = re.compile(r"(频道|广播电视(总)?台)")
        clean_name = pattern.sub("", channel_name).strip()
        return self._channel_name_map.get(clean_name, clean_name)

    def get_channel_id(self, channel_id: str) -> str:
        # channel_id = channel_id.replace("频道", "").replace("广播电视台", "")
        return self._channel_id_map.get(channel_id, channel_id)


config_manager = ConfigManager()
