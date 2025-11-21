from collections import defaultdict

from services import category_manager


class LiveMerger:
    def __init__(self, data):
        self._data = data
        self._host_cache = {}
        self._top_hosts = []
        self._filtered_data = defaultdict(list)
        self._host_count = None

    def _extract_host(self, url):
        """从URL中提取主机部分（IP或域名+端口），使用缓存优化"""
        if url in self._host_cache:
            return self._host_cache[url]

        try:
            host = url.split("//")[1].split("/")[0]
        except IndexError:
            host = None

        self._host_cache[url] = host
        return host

    def _count_host_channels(self):
        """统计每个主机的频道数量，使用缓存优化"""
        if self._host_count is not None:
            return self._host_count

        host_count = defaultdict(int)
        for _, _, url in self._data:
            host = self._extract_host(url)
            if host:
                host_count[host] += 1

        self._host_count = host_count
        return host_count

    def find_top_hosts(self, n=3):
        """找出频道数量最多的n个主机，优化排序逻辑"""
        if self._top_hosts:
            return self._top_hosts

        host_count = self._count_host_channels()

        # 使用堆队列优化最大n个元素的查找
        import heapq
        self._top_hosts = heapq.nlargest(n, host_count.items(), key=lambda x: x[1])
        return self._top_hosts

    def _filter_channels(self):
        """根据top主机过滤频道数据，优化集合操作"""
        if self._filtered_data:
            return self._filtered_data

        if not self._top_hosts:
            self.find_top_hosts()

        top_host_set = {host for host, _ in self._top_hosts}

        # 使用生成器表达式减少内存占用
        filtered_items = (
            (category, subgenre, url)
            for category, subgenre, url in self._data
            if self._extract_host(url) in top_host_set or category_manager.is_ignore(category)
        )

        for category, subgenre, url in filtered_items:
            self._filtered_data[category].append((subgenre, url))

        return self._filtered_data

    def format_output(self):
        """格式化输出结果，添加host统计信息"""
        if not self._filtered_data:
            self._filter_channels()
        if not self._top_hosts:
            self.find_top_hosts()

        # 生成host统计信息
        host_stats = [f"#{host}: {count}" for host, count in self._top_hosts]

        # 生成频道数据部分
        channel_data = []
        for category, items in self._filtered_data.items():
            category_info = category_manager.get_category_info(category)
            icon = category_info.get("icon", "") if category_info else ""
            category_title = f"{icon}{category},#genre#"
            channel_data.extend([category_title, *[f"{subgenre},{url}" for subgenre, url in items], ""])

        # 组合输出
        return "\n".join([
            "#========================",
            *host_stats,
            "#========================",
            *channel_data
        ])
