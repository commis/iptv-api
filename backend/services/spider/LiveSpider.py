from typing import Dict

from services.spider.base import register_spider, BaseSpider


@register_spider("live")
class LiveSpider(BaseSpider):
    def get_list_data(self, t: str, pg: int) -> Dict:
        return {"list": ["live1", "live2"], "total": 2}

    def get_detail_data(self, ids: str) -> Dict:
        return {"live_url": "xxx", "title": "直播"}

    def search_data(self, keyword: str, pg: int) -> Dict:
        return {"list": []}

    async def collect(self, is_full: bool = False) -> Dict:
        return {"success": 5, "fail": 0}
