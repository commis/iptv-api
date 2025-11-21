category_map = {
    '央视频道': '央视',
    '卫视频道': '卫视',
    '纪录频道': '纪录',
    '体育频道': '体育',
    '电影频道': '电影',
    '儿童频道': '儿童',
    '综艺频道': '综艺',
    '浙江频道': '地方',
}

channel_map = {
    'CCTV1': 'CCTV1综合',
    'CCTV2': 'CCTV2财经',
    'CCTV3': 'CCTV3综艺',
    'CCTV4': 'CCTV4中文国际',
    'CCTV5': 'CCTV5体育',
    'CCTV5+': 'CCTV5+体育赛事',
    'CCTV6': 'CCTV6电影',
    'CCTV7': 'CCTV7国防军事',
    'CCTV8': 'CCTV8电视剧',
    'CCTV9': 'CCTV9纪录',
    'CCTV10': 'CCTV10科教',
    'CCTV11': 'CCTV11戏曲',
    'CCTV12': 'CCTV12社会与法',
    'CCTV13': 'CCTV13新闻',
    'CCTV14': 'CCTV14少儿',
    'CCTV15': 'CCTV15音乐',
    'CCTV16': 'CCTV16奥林匹克',
    'CCTV17': 'CCTV17农业农村',
    'CGTN': 'CGTN英语',
    'CGTN记录': 'CGTN纪录',
    'CGTN外语纪录': 'CGTN纪录',
    'CGTN西语': 'CGTN西班牙语',
    'CGTN阿语': 'CGTN阿拉伯语',
    "CCTV风云音乐": '风云音乐',
    "CCTV风云足球": '风云足球',
    "CCTV风云剧场": '风云剧场',
    "CCTV怀旧剧场": '怀旧剧场',
    "CCTV兵器科技": '兵器科技',
    "CCTV世界地理": '世界地理',
    "CCTV央视台球": '央视台球',
    "CCTV第一剧场": '第一剧场',
    "CCTV女性时尚": '女性时尚',
    '中国农林卫视': '农林卫视',
    '体育休闲': '江苏体育休闲',
    '山东教育卫视': '山东教育',
    '公共新闻': '江苏新闻',
    '财富天下': '江苏财富天下',
    '北京纪实': '北京体育休闲',
}


class Const:

    @staticmethod
    def get_category(category_name: str) -> str:
        return category_map.get(category_name, category_name)

    @staticmethod
    def get_channel(channel_name: str) -> str:
        channel_name = channel_name.replace('频道', '')
        return channel_map.get(channel_name, channel_name)
