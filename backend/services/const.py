CATEGORY_MAP = {
    "央视": "央视频道",
    "卫视": "卫视频道",
    "超清": "超清频道",
    "地方": "地方频道",
    "纪录": "纪录频道",
    "体育": "体育频道",
    "电影": "电影频道",
    "儿童": "儿童频道",
    "综艺": "综艺频道",
    "地方": "浙江频道",
    "其他": "其他频道",
}

CHANNEL_ID_MAP = {
    "CCTV1综合": "CCTV1",
    "CCTV2财经": "CCTV2",
    "CCTV3综艺": "CCTV3",
    "CCTV4中文国际": "CCTV4",
    "CCTV5体育": "CCTV5",
    "CCTV5+体育赛事": "CCTV5+",
    "CCTV6电影": "CCTV6",
    "CCTV7国防军事": "CCTV7",
    "CCTV8电视剧": "CCTV8",
    "CCTV9纪录": "CCTV9",
    "CCTV10科教": "CCTV10",
    "CCTV11戏曲": "CCTV11",
    "CCTV12社会与法": "CCTV12",
    "CCTV13新闻": "CCTV13",
    "CCTV14少儿": "CCTV14",
    "CCTV15音乐": "CCTV15",
    "CCTV16奥林匹克": "CCTV16",
    "CCTV17农业农村": "CCTV17",
}

CHANNEL_MAP = {
    "CCTV1": "CCTV1综合",
    "CCTV2": "CCTV2财经",
    "CCTV3": "CCTV3综艺",
    "CCTV4": "CCTV4中文国际",
    "CCTV5": "CCTV5体育",
    "CCTV5+": "CCTV5+体育赛事",
    "CCTV6": "CCTV6电影",
    "CCTV7": "CCTV7国防军事",
    "CCTV8": "CCTV8电视剧",
    "CCTV9": "CCTV9纪录",
    "CCTV10": "CCTV10科教",
    "CCTV11": "CCTV11戏曲",
    "CCTV12": "CCTV12社会与法",
    "CCTV13": "CCTV13新闻",
    "CCTV14": "CCTV14少儿",
    "CCTV15": "CCTV15音乐",
    "CCTV16": "CCTV16奥林匹克",
    "CCTV17": "CCTV17农业农村",
    "CETV1": "CETV-1",
    "CETV2": "CETV-2",
    "CETV4": "CETV-4",
    "CGTN": "CGTN英语",
    "CGTN记录": "CGTN纪录",
    "CGTN外语纪录": "CGTN纪录",
    "CGTN西语": "CGTN西班牙语",
    "CGTN阿语": "CGTN阿拉伯语",
    "CCTV风云音乐": "风云音乐",
    "CCTV风云足球": "风云足球",
    "CCTV风云剧场": "风云剧场",
    "CCTV怀旧剧场": "怀旧剧场",
    "CCTV兵器科技": "兵器科技",
    "CCTV世界地理": "世界地理",
    "CCTV央视台球": "央视台球",
    "CCTV第一剧场": "第一剧场",
    "CCTV女性时尚": "女性时尚",
    "中国农林卫视": "农林卫视",
    "体育休闲": "江苏体育休闲",
    "山东教育卫视": "山东教育",
    "公共新闻": "江苏新闻",
    "财富天下": "江苏财富天下",
    "北京纪实": "北京体育休闲",
}


class Const:

    @staticmethod
    def get_category(category_name: str) -> str:
        return CATEGORY_MAP.get(category_name, category_name)

    @staticmethod
    def get_channel(channel_name: str) -> str:
        channel_name = channel_name.replace("频道", "")
        return CHANNEL_MAP.get(channel_name, channel_name)

    @staticmethod
    def get_channel_id(channel_id: str) -> str:
        return CHANNEL_ID_MAP.get(channel_id, channel_id)
