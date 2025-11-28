import threading
from typing import Dict, Optional

from core.singleton import singleton


@singleton
class CategoryManager:
    """
    管理分类与图标映射关系的单例类
    """

    _channel_relations: Dict[str, Dict[str, object]] = {}

    def __init__(self):
        # 分类信息，channels仅为配置，内存中的数据不存在
        self._categories: Dict[str, Dict[str, object]] = {
            "锻炼": {},
            "央视": {
                "channels": [],
                "excludes": ["精选推荐", "熊猫直播", "直播中国", "支持作者"],
            },
            "精品": {
                "channels": [
                    "风云音乐",
                    "风云足球",
                    "风云剧场",
                    "怀旧剧场",
                    "兵器科技",
                    "世界地理",
                    "央视台球",
                    "第一剧场",
                    "女性时尚",
                    "电视指南",
                    "老故事",
                    "中学生",
                    "发现之旅",
                ],
                "excludes": [],
            },
            "卫视": {
                "channels": [
                    "农林卫视",
                ],
                "excludes": [
                    "北京体育",
                    "金鹰纪实",
                    "上海纪实",
                    "上海卫视",
                ],
            },
            "超清": {
                "channels": [],
                "excludes": [],
            },
            "地方": {
                "channels": ["北京文艺", "北京新闻", "北京影视", "江苏财富天下"],
                "excludes": ["爱上海", "现代教育"],
            },
            "纪实": {
                "channels": [
                    "新动力量创一流",
                    "航拍中国第二季",
                    "环球旅游",
                    "军事评论",
                    "农业致富",
                    "探索发现",
                    "地理中国",
                    "人与自然",
                    "中国村庄",
                    "自然传奇",
                    "之江纪录",
                ],
                "excludes": [],
            },
            "体育": {
                "channels": [
                    "五星体育",
                    "北京体育休闲",
                    "江苏体育休闲",
                    "陕西体育休闲",
                    "赛事最经典",
                    "体坛名栏汇",
                    "四海钓鱼",
                    "快乐垂钓",
                    "武术世界",
                    "天元围棋",
                    "24小时城市联赛轮播台",
                    "24小时全运会轮播台",
                ],
                "excludes": [],
            },
            "综艺": {"channels": ["最强综艺趴"], "excludes": []},
            "教育": {
                "channels": ["CETV-1", "CETV-2", "CETV-4", "山东教育"],
                "excludes": [],
            },
            "电影": {
                "channels": [
                    "CHC电影",
                    "CHC动作电影",
                    "CHC家庭影院",
                    "CHC影迷电影",
                    "黑莓电影",
                    "南方影视",
                    "经典香港电影",
                    "抗战经典影片",
                    "新片放映厅",
                    "高清大片",
                    "东森电影",
                    "凤凰电影",
                    "龙华电影",
                    "重温经典",
                ],
                "excludes": [
                    "淘剧场",
                    "淘娱乐",
                    "韩国电影1",
                    "韩国电影2",
                    "倩女幽魂道道道",
                    "倩女幽魂人间道",
                    "倩女幽魂妖魔道",
                ],
            },
            "儿童": {
                "channels": [
                    "哈哈炫动",
                    "金鹰卡通",
                    "嘉佳卡通",
                    "卡酷少儿",
                    "优漫卡通",
                    "黑龙江少儿",
                    "浙江少儿",
                    "广东少儿",
                    "经典动画大集合",
                ],
                "excludes": ["韩国EBS少儿"],
            },
            "英语": {},
            "科学": {},
            "地理": {},
            "历史": {},
            "生物": {},
            "纪录": {"channels": [], "excludes": ["*"]},
            "寰宇": {},
            "寻味": {},
            "人物": {},
            "战争": {},
            "文化": {},
            "其他": {"channels": ["钱塘江"]},
            "直播": {},
            "熊猫": {},
            "春晚": {},
        }
        self._lock = threading.RLock()
        self._ignore_categories = ["直播", "熊猫", "春晚", "港台", "海外", "全球"]

        self._init_channel_relations()

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


category_manager = CategoryManager()
