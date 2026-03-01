# constants.py
import os
import re


class Constants:
    """项目公共常量类，包含所有业务需要的常量定义"""

    # 合并正则：移除表情符号、逗号、#genre#和多余空格
    CATEGORY_CLEAN_PATTERN = re.compile(
        r'[\U0001F000-\U0001FFFF\U00002500-\U00002BEF\U00002E00-\U00002E7F\U00003000-\U00003300,#genre#\s]+')

    # 网络请求相关常量，不要小于10秒
    REQUEST_TIMEOUT = 10

    # 线程池相关常量
    IO_INTENSITY_FACTOR = 4  # 可在2-8之间调整

    _MIGU_CID_MAP = {
        "CCTV1综合": "cctv1",
        "CCTV2财经": "cctv2",
        "CCTV3综艺": "cctv3",
        "CCTV4中文国际": "cctv4",
        "CCTV5体育": "cctv5",
        "CCTV5+体育赛事": "cctv5plus",
        "CCTV6电影": "cctv6",
        "CCTV7国防军事": "cctv7",
        "CCTV8电视剧": "cctv8",
        "CCTV9纪录": "cctvjilu",
        "CCTV10科教": "cctv10",
        "CCTV11戏曲": "cctv11",
        "CCTV12社会与法": "cctv12",
        "CCTV13新闻": "cctv13",
        "CCTV14少儿": "cctvchild",
        "CCTV15音乐": "cctv15",
        "CCTV17农业农村": "cctv17",
        "CCTV4欧洲": "cctveurope",
        "CCTV4美洲": "cctvamerica",
    }

    @classmethod
    def get_cvt_name(cls, key: str):
        return cls._MIGU_CID_MAP.get(key, key)

    @classmethod
    def cvt_exist(cls, key: str):
        return key in cls._MIGU_CID_MAP

    MIGU_USERID = os.getenv("muserId")
    MIGU_TOKEN = os.getenv("mtoken")

    _MIGU_IDS = {
        # 央视频道
        "cctv1": {"pid": "608807420", "name": "CCTV1综合"},
        "cctv2": {"pid": "631780532", "name": "CCTV2财经"},
        "cctv3": {"pid": "624878271", "name": "CCTV3综艺"},
        "cctv4": {"pid": "631780421", "name": "CCTV4中文国际"},
        "cctv4a": {"pid": "608807416", "name": "CCTV4美洲"},
        "cctv4o": {"pid": "608807419", "name": "CCTV4欧洲"},
        "cctv5": {"pid": "641886683", "name": "CCTV5体育"},
        "cctv5p": {"pid": "641886773", "name": "CCTV5+体育赛事"},
        "cctv6": {"pid": "624878396", "name": "CCTV6电影"},
        "cctv7": {"pid": "673168121", "name": "CCTV7国防军事"},
        "cctv8": {"pid": "624878356", "name": "CCTV8电视剧"},
        "cctv9": {"pid": "673168140", "name": "CCTV9纪录"},
        "cctv10": {"pid": "624878405", "name": "CCTV10科教"},
        "cctv11": {"pid": "667987558", "name": "CCTV11戏曲"},
        "cctv12": {"pid": "673168185", "name": "CCTV12社会与法"},
        "cctv13": {"pid": "608807423", "name": "CCTV13新闻"},
        "cctv14": {"pid": "624878440", "name": "CCTV14少儿"},
        "cctv15": {"pid": "673168223", "name": "CCTV15音乐"},
        "cctv16": {"pid": "", "name": "CCTV16奥林匹克"},
        "cctv17": {"pid": "673168256", "name": "CCTV17农业农村"},
        "cetv1": {"pid": "923287154", "name": "CETV1"},
        "cetv2": {"pid": "923287211", "name": "CETV2"},
        "cetv4": {"pid": "923287339", "name": "CETV4"},
        "cgtn": {"pid": "609017205", "name": "CGTN"},
        "cgtnjl": {"pid": "609006487", "name": "CGTN外语纪录"},
        "cgtnx": {"pid": "609006450", "name": "CGTN西班牙语"},
        "cgtnf": {"pid": "609006476", "name": "CGTN法语"},
        "cgtna": {"pid": "609154345", "name": "CGTN阿拉伯语"},
        "cgtne": {"pid": "609006446", "name": "CGTN俄语"},
        "fxzl": {"pid": "624878970", "name": "发现之旅"},
        "lgs": {"pid": "884121956", "name": "老故事"},
        "zxs": {"pid": "708869532", "name": "中学生"},

        # 卫视频道
        "ahws": {"pid": "", "name": "安徽卫视"},
        "bjws": {"pid": "630287636", "name": "北京卫视"},
        "btws": {"pid": "956923145", "name": "兵团卫视"},
        "dfws": {"pid": "651632648", "name": "东方卫视"},
        "dnws": {"pid": "849116810", "name": "东南卫视-NOK"},
        "gsws": {"pid": "", "name": "甘肃卫视"},
        "gdws": {"pid": "608831231", "name": "广东卫视"},
        "gxws": {"pid": "", "name": "广西卫视"},
        "gzws": {"pid": "", "name": "贵州卫视"},
        "hinws": {"pid": "738906860", "name": "海南卫视-NOK"},
        "hbws": {"pid": "962042070", "name": "河北卫视"},
        "hnws": {"pid": "790187291", "name": "河南卫视"},
        "hljws": {"pid": "", "name": "黑龙江卫视"},
        "dwqws": {"pid": "608917627", "name": "大湾区卫视"},
        "hubws": {"pid": "947472496", "name": "湖北卫视"},
        "hunws": {"pid": "", "name": "湖南卫视"},
        "jlws": {"pid": "738906889", "name": "吉林卫视-NOK"},
        "jsws": {"pid": "623899368", "name": "江苏卫视"},
        "jxws": {"pid": "783847495", "name": "江西卫视"},
        "lnws": {"pid": "630291707", "name": "辽宁卫视"},
        "nmgws": {"pid": "", "name": "内蒙古卫视"},
        "nlws": {"pid": "956904896", "name": "农林卫视"},
        "qhws": {"pid": "738898486", "name": "青海卫视-NOK"},
        "sdws": {"pid": "", "name": "山东卫视"},
        "sxiws": {"pid": "", "name": "山西卫视"},
        "sxws": {"pid": "738910838", "name": "陕西卫视"},
        "scws": {"pid": "", "name": "四川卫视"},
        "szws": {"pid": "", "name": "深圳卫视"},
        "tjws": {"pid": "", "name": "天津卫视"},
        "xzws": {"pid": "", "name": "西藏卫视"},
        "ynws": {"pid": "", "name": "云南卫视"},
        "zjws": {"pid": "", "name": "浙江卫视"},
        "cqws": {"pid": "738910914", "name": "重庆卫视"},
        "nxws": {"pid": "738910535", "name": "宁夏卫视"},

        # 4K频道
        "bjws4k": {"pid": "", "name": "北京卫视4K"},
        "dfws4k": {"pid": "", "name": "东方卫视4K"},
        "hunws4k": {"pid": "", "name": "湖南卫视4K"},
        "jsws4k": {"pid": "", "name": "江苏卫视4K"},
        "szws4k": {"pid": "", "name": "深圳卫视4K"},
        "zjws4k": {"pid": "", "name": "浙江卫视4K"},
        "hb4k": {"pid": "", "name": "河北4K"},
        "sz4k": {"pid": "", "name": "苏州4K"},

        # 地方频道-北京
        "bjcj": {"pid": "", "name": "北京财经"},
        "bjjs": {"pid": "", "name": "北京科教"},
        "bjsh": {"pid": "", "name": "北京生活"},
        "bjty": {"pid": "", "name": "北京体闲"},
        "bjwy": {"pid": "", "name": "北京文艺"},
        "bjxw": {"pid": "", "name": "北京新闻"},
        "bjys": {"pid": "", "name": "北京影视"},
        # 地方频道-上海
        "shxwzh": {"pid": "651632657", "name": "上海新闻综合"},
        "sdsdfys": {"pid": "617290047", "name": "上视东方影视"},
        # 地方频道-广东
        "gdty": {"pid": "", "name": "广东体育"},
        "gdzj": {"pid": "", "name": "广东珠江"},
        # 地方频道-深圳
        # 地方频道-江苏
        "cftx": {"pid": "956923159", "name": "财富天下"},
        "jsggxw": {"pid": "626064693", "name": "江苏公共新闻"},
        "jyxwzh": {"pid": "955227979", "name": "江阴新闻综合"},
        "lsxwzh": {"pid": "639737327", "name": "溧水新闻综合"},
        "ntxwzh": {"pid": "955227985", "name": "南通新闻综合"},
        "ycxwzh": {"pid": "639731825", "name": "盐城新闻综合"},
        "yxxwzh": {"pid": "955227996", "name": "宜兴新闻综合"},
        # 地方频道-辽宁
        "lngg": {"pid": "962045223", "name": "辽宁公共"},
        "lnsheng": {"pid": "962045226", "name": "辽宁生活"},
        "lntyxx": {"pid": "962067526", "name": "辽宁体育休闲"},
        "lnyingshi": {"pid": "962067517", "name": "辽宁影视剧"},
        # 地方频道-宁夏
        "nxjj": {"pid": "962067520", "name": "宁夏经济"},
        "nxwl": {"pid": "962067523", "name": "宁夏文旅"},
        # 地方频道-陕西
        "sxdsqc": {"pid": "956909358", "name": "陕西都市青春"},
        "sxqq": {"pid": "956909303", "name": "陕西秦腔"},
        "sxxwzx": {"pid": "956909289", "name": "陕西新闻资讯"},
        "sxyinling": {"pid": "956909362", "name": "陕西银龄"},
        "sxtyxx": {"pid": "956909362", "name": "陕西体育休闲"},

        # 教育频道
        "sdjy": {"pid": "609154353", "name": "山东教育"},

        # 综艺频道
        "zqzyp": {"pid": "629942228", "name": "最强综艺趴"},

        # 纪实频道
        "xdlcyl": {"pid": "713589837", "name": "新动力量创一流"},

        # 体育频道
        "jbty": {"pid": "", "name": "劲爆体育"},
        "wxty": {"pid": "", "name": "五星体育"},
        "sihai": {"pid": "637444975", "name": "四海钓鱼"},
        "ttmlh": {"pid": "629943305", "name": "体坛名栏汇"},
        "sszjd": {"pid": "646596895", "name": "赛事最经典"},
        "sxty": {"pid": "956909356", "name": "陕西体育"},
        "mg24hty": {"pid": "654102378", "name": "咪咕24小时体育台"},

        # 影视频道
        "chcym": {"pid": "952383261", "name": "CHC影迷电影"},
        "chcjt": {"pid": "644368373", "name": "CHC家庭影院"},
        "chcdz": {"pid": "644368714", "name": "CHC动作电影"},
        "jdxgdy": {"pid": "625703337", "name": "经典香港电影"},
        "kzjdyp": {"pid": "617432318", "name": "抗战经典影片"},
        "gqdp": {"pid": "644368714", "name": "高清大片"},
        "xpfyt": {"pid": "619495952", "name": "新片放映厅"},
        "xdm": {"pid": "644368714", "name": "新动漫"},
        "jddhdjh": {"pid": "629942219", "name": "经典动画大集合"},
        "hmxt": {"pid": "713591450", "name": "和美乡途轮播台"},
    }

    @classmethod
    def get_migu_list(cls):
        return [f"{k} -> {v}" for k, v in cls._MIGU_IDS.items()]

    @classmethod
    def get_migu_cid(cls, key: str):
        return cls._MIGU_IDS.get(key, '000000000')
