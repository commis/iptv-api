import os
import threading
from typing import Dict, Optional, Any

import yaml

from core.singleton import singleton


@singleton
class CategoryManager:
    """
    管理分类与图标映射关系的单例类
    """

    _channel_relations: Dict[str, Dict[str, object]] = {}

    def __init__(self, config_path: str = None):
        self._lock = threading.RLock()

        # 初始化加载配置
        self._config_path = config_path or os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "..",
                "spider",
                "dist",
                "service.yaml",
            )
        )
        full_config = self._load_config()
        self._category_map: Dict[str, str] = full_config["category_map"]
        self._ignore_categories: Dict[str, str] = full_config["ignore_category"]
        self._channel_id_map: Dict[str, str] = full_config["channel_id_map"]
        self._channel_name_map: Dict[str, str] = full_config["channel_name_map"]
        self._categories: Dict[str, Dict[str, Any]] = full_config["channel_map"]

        self._init_channel_relations()

    def _load_config(self) -> Dict[str, Any]:
        """加载完整配置（仅临时使用）"""
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(
                f"the config is not exist, file：{self._config_path}\n"
                f"Please check spider/service.yaml file"
            )

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
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
        with self._lock:
            for category_name, category_info in self._categories.items():
                category_info.update({"name": category_name})
                category_info.update({"excludes": category_info.get("excludes", [])})
                channel_list = category_info.get("channels", [])
                for channel in channel_list:
                    self._channel_relations[channel] = category_info

    def is_ignore(self, category: str):
        """判断是否为忽略的分类"""
        return category in self._ignore_categories

    def is_exclude(self, category_info: {}, channel_name: str) -> bool:
        """判断是否为排除的频道"""
        channels = category_info.get("channels", [])
        excludes = category_info.get("excludes", [])
        return (
            "*" in excludes and channel_name not in channels
        ) or channel_name in excludes

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
        if channel_name in self._channel_relations:
            return self._channel_relations[channel_name]
        else:
            info = self._categories.get(category_name)
            return self._categories.get("未分类组") if info is None else info

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
        channel_name = channel_name.replace("频道", "")
        return self._channel_name_map.get(channel_name, channel_name)

    def get_channel_id(self, channel_id: str) -> str:
        return self._channel_id_map.get(channel_id, channel_id)


category_manager = CategoryManager()
