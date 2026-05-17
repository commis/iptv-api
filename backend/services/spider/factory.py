import importlib
from pathlib import Path
from typing import Dict, Type

from core.logger_factory import LoggerFactory
from services.spider.base import BaseSpider

logger = LoggerFactory.get_logger(__name__)

SPIDER_DIR = Path(__file__).parent
SPIDER_REGISTRY: Dict[str, Type["BaseSpider"]] = {}


def register_spider(sp: str):
    """
    【自动注册装饰器】
    给每个爬虫类加上 @register_spider("my-sp") 即可自动注册
    无需手动维护 MAP
    """

    def decorator(cls: Type[BaseSpider]):
        SPIDER_REGISTRY[sp] = cls
        return cls

    return decorator


class SpiderFactory:

    @staticmethod
    def auto_discover_spiders():
        """自动扫描并加载所有 *Spider.py 文件"""
        for py_file in SPIDER_DIR.glob("*Spider.py"):
            if py_file.stem == "__init__":
                continue

            module_name = f"services.spider.{py_file.stem}"
            try:
                # 动态导入模块，触发装饰器注册
                importlib.import_module(module_name)
                logger.info(f"[SpiderAutoLoad] 已加载爬虫模块: {module_name}")
            except Exception as e:
                logger.error(f"[SpiderAutoLoad] 加载模块失败 {module_name}: {e}")

    @staticmethod
    def get_spider(sp: str) -> BaseSpider | None:
        spider_cls = SPIDER_REGISTRY.get(sp)
        if not spider_cls:
            return None
        return spider_cls(sp)

    @staticmethod
    def exist_sp(sp: str) -> bool:
        return sp in SPIDER_REGISTRY

    @staticmethod
    def list_all_spiders():
        if not SPIDER_REGISTRY:
            SpiderFactory.auto_discover_spiders()
        return list(SPIDER_REGISTRY.keys())


SpiderFactory.auto_discover_spiders()
