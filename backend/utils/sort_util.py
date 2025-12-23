import re
from typing import List, Tuple, Optional


class StringSorter:
    """字符串混合排序工具类"""

    __CHINESE_NUM_MAP = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "百": 100,
        "千": 1000,
        "万": 10000,
    }

    # 正则表达式定义
    __PURE_NUM = re.compile(r"^\d+$")
    __PURE_EN = re.compile(r"^[a-zA-Z\+\-]*$")
    __PURE_CN = re.compile(r"^[\u4e00-\u9fa5]+$")
    __ONLY_SPECIAL = re.compile(r"^[!#@]+$")
    __HAS_NUM = re.compile(r"\d")
    __HAS_EN = re.compile(r"[a-zA-Z]")
    __HAS_CN = re.compile(r"[\u4e00-\u9fa5]")
    __HAS_SPECIAL = re.compile(r"[!#@]")
    __CN_NUM_CHAR = "".join(__CHINESE_NUM_MAP.keys())
    __SPLIT_PATTERN = re.compile(
        rf"([!#@]+)|(\d+)|([a-zA-Z]+)|([{__CN_NUM_CHAR}]+)|([\u4e00-\u9fa5])|([+-]+)|([^\d\w\u4e00-\u9fa5!#@+-]+)"
    )
    __CN_NUM_PATTERN = re.compile(rf"[{__CN_NUM_CHAR}]+")

    @classmethod
    def __parse_chinese_num(cls, cn_str: str) -> int:
        """解析连续中文数字字符串（支持十/百/千/万组合，如：十二=12，一百二十三=123）"""
        if not cn_str or not cls.__CN_NUM_PATTERN.fullmatch(cn_str):
            return 0

        result = 0
        temp = 0
        for char in cn_str:
            num = cls.__CHINESE_NUM_MAP[char]
            if num >= 10:  # 十/百/千/万
                if temp == 0:
                    temp = 1  # 处理“十”=10，“百”=100（无前置数）
                result += temp * num
                temp = 0
            else:  # 0-9
                temp = temp * 10 + num
        result += temp
        return result

    @classmethod
    def __get_start_type(cls, s: str) -> int:
        """获取字符串开头类型（排序优先级）：0=数字开头 1=字母开头 2=汉字开头 3=特殊字符开头 4=空/其他"""
        s_stripped = s.strip()
        if not s_stripped:
            return 4
        first_char = s_stripped[0]
        if first_char.isdigit() or first_char in cls.__CHINESE_NUM_MAP:
            return 0  # 数字开头（含中文数字）
        elif first_char.isalpha():
            return 1  # 字母开头
        elif first_char in "\u4e00-\u9fa5":
            return 2  # 汉字开头
        elif first_char in "!#@":
            return 3  # 特殊字符开头
        else:
            return 4  # 其他/空

    @classmethod
    def __extract_start_num(cls, s: str) -> float:
        """提取开头数字（含中文数字），非数字开头返回inf"""
        s_stripped = s.strip()
        if not s_stripped:
            return float("inf")

        # 匹配开头连续阿拉伯数字
        num_match = re.match(r"^\d+", s_stripped)
        if num_match:
            return int(num_match.group())

        # 匹配开头连续中文数字
        cn_num_match = re.match(rf"^[{cls.__CN_NUM_CHAR}]+", s_stripped)
        if cn_num_match:
            return cls.__parse_chinese_num(cn_num_match.group())

        return float("inf")

    @classmethod
    def __mixed_sort_key(cls, s: str) -> Tuple[int, float, Tuple, int]:
        """
        生成排序键（严格匹配5条规则）
        排序优先级：开头类型 → 开头数字值 → 拆分后片段 → 字符串长度
        """
        s_stripped = s.strip()
        # 规则1：数字开头优先按数字排序
        start_type = cls.__get_start_type(s_stripped)
        start_num = cls.__extract_start_num(s_stripped)
        key_parts = []

        # 片段处理规则（按规则3/4/5）
        type_rules = [
            # 1. 阿拉伯数字：转整数排序
            (lambda p: p.isdigit(), lambda p: ("num", int(p))),
            # 2. 中文数字：解析为整数排序（规则5）
            (
                lambda p: cls.__CN_NUM_PATTERN.fullmatch(p),
                lambda p: ("num", cls.__parse_chinese_num(p)),
            ),
            # 3. 字母：先小写再大写（规则2：a < A < b < B）
            (lambda p: p.isalpha(), lambda p: ("en", (p.lower(), p))),
            # 4. 特殊字符：按ASCII码排序
            (lambda p: p[0] in "!#@", lambda p: ("special", (ord(p[0]), p))),
            # 5. 汉字：按拼音小写排序
            (
                lambda p: cls.__HAS_CN.match(p),
                lambda p: ("cn", "".join(lazy_pinyin(p)).lower()),
            ),
            # 6. 符号（+-）：按ASCII码排序
            (lambda p: p in "+-", lambda p: ("symbol", ord(p))),
            # 7. 其他字符：按原字符串排序
            (lambda p: True, lambda p: ("other", p)),
        ]

        # 拆分字符串并生成片段排序键
        for part in cls.__SPLIT_PATTERN.findall(s_stripped):
            part = next(p for p in part if p)  # 取非空片段
            if not part:
                continue
            for check, handle in type_rules:
                if check(part):
                    key_parts.append(handle(part))
                    break

        str_len = len(s_stripped) if s_stripped else 0
        # 最终排序键：开头类型 → 开头数字 → 拆分片段 → 字符串长度
        return start_type, start_num, tuple(key_parts), str_len

    @staticmethod
    def get_sort_key(s: str):
        return StringSorter.__mixed_sort_key(s)

    @staticmethod
    def mixed_sort(str_list: List[str]) -> List[str]:
        return sorted(str_list, key=StringSorter.__mixed_sort_key)
