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
        'cctv1': '608807420',  # CCTV1综合
        'cctv2': '672926537',  # CCTV2财经
        'cctv3': '624878270',  # CCTV3综艺
        'cctv4': '672924435',  # CCTV4中文国际
        'cctv4o': '608807419',  # CCTV4中文国际欧洲
        'cctv4a': '608807416',  # CCTV4中文国际美洲
        'cctv5': '641886681',  # CCTV5体育
        'cctv5p': '641886771',  # CCTV5+体育赛事
        'cctv6': '624878393',  # CCTV6电影
        'cctv7': '673168121',  # CCTV7国防军事
        'cctv8': '624878355',  # CCTV8电视剧
        'cctv9': '673168140',  # CCTV9纪录
        'cctv10': '624878405',  # CCTV10科教
        'cctv11': '672923822',  # CCTV11戏曲
        'cctv12': '673168185',  # CCTV12社会与法
        'cctv13': '672922360',  # CCTV13新闻
        'cctv14': '624878440',  # CCTV14少儿
        'cctv15': '673168223',  # CCTV15音乐
        'cctv17': '673168256',  # CCTV17农村农业
        'bqkj': '623338073',  # CCTV兵器科技
        'hjjc': '623364608',  # CCTV怀旧剧场
        'fyjc': '623338051',  # CCTV风云剧场
        'fyyy': '623338072',  # CCTV风云音乐
        'fyzq': '621984939',  # CCTV风云足球
        'sjdl': '623338083',  # CCTV世界地理
        'whjp': '623338084',  # CCTV文化精品
        'ystq': '603842910',  # CCTV央视台球
        'gefwq': '621984921',  # CCTV高尔夫网球
        'nxss': '623338081',  # CCTV女性时尚
        'dyjc': '623338041',  # CCTV第一剧场
        'cgtn': '609017205',  # CGTN
        'cgtnjl': '609006487',  # CGTN纪录
        'cgtna': '609154345',  # CGTN阿拉伯语
        'cgtnf': '609006476',  # CGTN法语
        'cgtne': '609006450',  # CGTN西班牙语
        'cgtnr': '609006446',  # CGTN俄语
        'cetv1': '649531734',  # CETV1中教1台
        'cetv2': '649532169',  # CETV2中教2台
        'cetv3': '649531756',  # CETV3中教3台
        'cetv4': '649531725',  # CETV4中教4台
        'bjws': '630287636',  # 北京卫视
        'dfws': '651625930',  # 东方卫视
        'cqws': '630288006',  # 重庆卫视
        'jlws': '630288397',  # 吉林卫视
        'lnws': '630291707',  # 辽宁卫视
        'nmws': '630287015',  # 内蒙古卫视
        'nxws': '630287436',  # 宁夏卫视
        'gsws': '630287549',  # 甘肃卫视
        'qhws': '630287272',  # 青海卫视
        'sxws': '630287233',  # 陕西卫视
        'hbws': '630292528',  # 河北卫视
        'sxiws': '630289043',  # 山西卫视
        'ahws': '644933992',  # 安徽卫视
        'hnws': '635489820',  # 河南卫视
        'hubws': '630292423',  # 湖北卫视
        'jxws': '630290852',  # 江西卫视
        'jsws': '623899540',  # 江苏卫视
        'dnws': '651642156',  # 东南卫视
        'gdws': '608831231',  # 广东卫视
        'nfws': '608917627',  # 南方卫视
        'gxws': '634055160',  # 广西卫视
        'ynws': '630291417',  # 云南卫视
        'gzws': '631094827',  # 贵州卫视
        'scws': '630288361',  # 四川卫视
        'xjws': '635385783',  # 新疆卫视
        'btws': '630288004',  # 兵团卫视
        'xzws': '630291593',  # 西藏卫视
        'bjdajs': '641874369',  # 北京冬奥纪实
        'shdy': '650999610',  # 四海钓鱼
        'shxwzh': '651632657',  # 上海新闻综合
        'dycj': '608780988',  # 第一财经
        'dfys': '617290047',  # 东方影视
        'dfds': '651642246',  # 东方都市
        'shjsrw': '617289997',  # 上视纪实人文
        'shics': '618894223',  # 上海ICS
        'fztd': '631095330',  # 法治天地
        'qjs': '623674483',  # 全纪实
        'sdjy': '609154353',  # 山东教育
        'sxys': '628472887',  # 山西影视
        'sxkj': '628472792',  # 山西科教
        'sxgg': '628472786',  # 山西公共
        'sxhh': '628473059',  # 山西黄河
        'jscs': '626064714',  # 江苏城市
        'jszy': '626065193',  # 江苏综艺
        'jsgg': '626064693',  # 江苏公共新闻
        'jsjy': '628008321',  # 江苏教育
        'jsgj': '626064674',  # 江苏国际
        'jsys': '626064697',  # 江苏影视
        'jsty': '626064707',  # 江苏体育休闲
        'wxxwzh': '639737327',  # 无锡新闻综合
        'czxwzg': '639731892',  # 常州新闻综合
        'yzxwzh': '639731888',  # 扬州新闻综合
        'szxwzh': '639731952',  # 苏州新闻综合
        'tzxwzh': '639731818',  # 泰州新闻综合
        'ycxwzh': '639731825',  # 盐城新闻综合
        'haxwzh': '639731826',  # 淮安新闻综合
        'zjxwzh': '639731783',  # 镇江新闻综合
        'xzxwzh': '639731747',  # 徐州新闻综合
        'sqxwzh': '639731832',  # 宿迁新闻综合
        'lygxwzh': '639731715',  # 连云港新闻综合
        'zjse': '611318244',  # 浙江少儿
        'hzys': '611373913',  # 杭州影视
        'hzzh': '611354772',  # 杭州综合
        'gqdp': '629943678',  # 高清大片
        'jdfyt': '626157533',  # 经典放映厅
        'xpfyt': '619495952',  # 新片放映厅
        'mg24hty': '654102378',  # 咪咕24小时体育台
        'zyxc': '621640581',  # 综艺现场
        'tsjl': '615809560',  # 探索纪录
    }

    @classmethod
    def get_migu_list(cls):
        return [f"{k} -> {v}" for k, v in cls._MIGU_IDS.items()]

    @classmethod
    def get_migu_cid(cls, key: str):
        return cls._MIGU_IDS.get(key, '000000000')
