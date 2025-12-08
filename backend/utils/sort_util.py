import re
from typing import List, Tuple, Optional


class StringSorter:
    """字符串混合排序工具类"""
    __CHINESE_NUM_MAP = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }

    __PURE_NUM = re.compile(r'^\d+$')
    __PURE_EN = re.compile(r'^[a-zA-Z\+\-]*$')
    __PURE_CN = re.compile(r'^[\u4e00-\u9fa5]+$')
    __ONLY_SPECIAL = re.compile(r'^[!#@]+$')
    __HAS_NUM = re.compile(r'\d')
    __HAS_EN = re.compile(r'[a-zA-Z]')
    __HAS_CN = re.compile(r'[\u4e00-\u9fa5]')
    __HAS_SPECIAL = re.compile(r'[!#@]')
    __SPLIT_PATTERN = re.compile(
        r'([!#@]+)|(\d+)|([a-zA-Z]+)|([' + ''.join(__CHINESE_NUM_MAP.keys()) + r'])|([\u4e00-\u9fa5])|([+-]+)'
    )

    @classmethod
    def __get_str_main_type(cls, s: str) -> int:
        s_stripped = s.strip()
        if not s_stripped:
            return 13

        hn = bool(cls.__HAS_NUM.search(s_stripped))
        he = bool(cls.__HAS_EN.search(s_stripped))
        hc = bool(cls.__HAS_CN.search(s_stripped))
        hs = bool(cls.__HAS_SPECIAL.search(s_stripped))
        pn = bool(cls.__PURE_NUM.match(s_stripped))
        pe = bool(cls.__PURE_EN.match(s_stripped))
        pc = bool(cls.__PURE_CN.match(s_stripped))
        os = bool(cls.__ONLY_SPECIAL.match(s_stripped))

        weight = next((w for cond, w in [
            (pn, 0), (hn and he and not hc and not hs, 1), (pe, 2),
            (hn and hs and not he and not hc, 3), (he and hs and not hn and not hc, 4),
            (hn and he and hs and not hc, 5), (pc, 6), (hn and hc and not he and not hs, 7),
            (he and hc and not hn and not hs, 8), (hc and hs and not hn and not he, 9),
            (hn and he and hc and not hs, 10), (hn and he and hc and hs, 11), (os, 12)
        ] if cond), 13)
        return weight

    @classmethod
    def __parse_chinese_num(cls, char: str) -> Optional[int]:
        return cls.__CHINESE_NUM_MAP.get(char)

    @classmethod
    def __mixed_sort_key(cls, s: str) -> Tuple[int, Tuple, int]:
        main_type = cls.__get_str_main_type(s)
        s_stripped = s.strip()
        key_parts = []

        type_rules = [
            (lambda p: p[0] in '!#@', lambda p: ('special', p)),
            (lambda p: p.isdigit() or p in cls.__CHINESE_NUM_MAP,
             lambda p: ('num', int(p) if p.isdigit() else cls.__parse_chinese_num(p))),
            (lambda p: p[0].isalpha(), lambda p: ('en', (p.lower(), p))),
            (lambda p: cls.__HAS_CN.match(p), lambda p: ('cn', p)),
            (lambda p: p in '+-', lambda p: ('symbol', p))
        ]

        for part in cls.__SPLIT_PATTERN.findall(s_stripped):
            part = next(p for p in part if p)
            if not part:
                continue
            for check, handle in type_rules:
                if check(part):
                    key_parts.append(handle(part))
                    break

        str_len = len(s_stripped) if s_stripped else 0
        return main_type, tuple(key_parts), str_len

    @staticmethod
    def get_sort_key(s: str):
        return StringSorter.__mixed_sort_key(s)

    @staticmethod
    def mixed_sort(str_list: List[str]) -> List[str]:
        return sorted(str_list, key=StringSorter.__mixed_sort_key)
