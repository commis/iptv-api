import re

from pypinyin import pinyin, Style

CHINESE_NUM_MAP = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def get_str_main_type(s):
    """
    扁平化重构：判断字符串的主类型并直接返回权重（数值越小优先级越高）
    类型优先级（从高到低）：
    符号(0) → 纯数字(1) → 数字+中文(2) → 数字+英文(3) → 数字+英文+中文(4) → 纯英文(5) → 纯中文(6)
    """
    # 提取字符串核心特征（仅计算一次，提升性能）
    has_symbol = bool(re.search(r'[^\w\s]', s))
    has_arabic_num = bool(re.search(r'\d', s))
    has_chinese_num = bool(re.search(r'[' + ''.join(CHINESE_NUM_MAP.keys()) + ']', s))
    has_english = bool(re.search(r'[a-zA-Z]', s))
    has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', s))
    has_num = has_arabic_num or has_chinese_num

    # 1. 符号类型：直接返回0（最高优先级）
    if has_symbol:
        return 0

    # 2. 含数字的场景（扁平判断，直接return）
    if has_num:
        # 纯数字（无英文、无中文）
        if not has_english and not has_chinese:
            return 1
        # 数字+中文（无英文）
        elif not has_english and has_chinese:
            return 2
        # 数字+英文（无中文）
        elif has_english and not has_chinese:
            return 3
        # 数字+英文+中文
        elif has_english and has_chinese:
            return 4

    # 3. 不含数字的场景（扁平判断，直接return）
    # 纯英文（无中文）
    if has_english and not has_chinese:
        return 5
    # 纯中文（无英文）
    elif has_chinese and not has_english:
        return 6

    # 4. 兜底（空字符串/仅空格等）：归为符号类型
    return 0


def mixed_sort_key(s):
    """
    混合排序键：同时支持数字自然排序和汉字拼音排序
    1. 按字母/符号顺序（ASCII码）
    2. 按数字大小（自然排序）
    3. 按汉字拼音（小写）
    """
    main_type = get_str_main_type(s)
    pattern = re.compile(r'([^\w\s]+)|(\d+)|([a-zA-Z]+)|([\u4e00-\u9fa5]+)')
    key_parts = []

    for match in pattern.finditer(s):
        symbol_part, num_part, english_part, chinese_part = match.groups()

        if symbol_part:
            key_parts.append(('s', symbol_part))
        elif num_part:
            key_parts.append(('n', int(num_part)))
        elif english_part:
            for char in english_part:
                key_parts.append(('e', (char.lower(), char)))
        elif chinese_part:
            # 汉字：数字转阿拉伯，普通汉字转拼音
            for char in chinese_part:
                if char in CHINESE_NUM_MAP:
                    key_parts.append(('n', CHINESE_NUM_MAP[char]))
                else:
                    pinyin_str = pinyin(char, style=Style.NORMAL, strict=False)[0][0].lower()
                    key_parts.append(('c', pinyin_str))

    str_length = len(s)
    return main_type, tuple(key_parts), str_length
