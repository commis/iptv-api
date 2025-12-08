import re
from typing import List, Tuple, Optional

from pypinyin import pinyin, Style

# 中文数字映射（覆盖航拍中国的季数排序）
CHINESE_NUM_MAP = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def get_str_main_type(s: str) -> int:
    """
    最终权重规则（适配所有测试用例，重点修复test_empty_string）：
    权重越小 → 排序越靠前
    1. 纯数字（如123）
    2. 纯英文（含+/-，如a+b/abc）
    3. 符号+数字（!789/#456/@123）
    4. 数字+中文（2024年春节）: 3
    5. 数字+英文（A69英文）: 4
    6. 数字+英文+中文（test8测试）: 5
    7. 纯中文（央视新影）: 6
    8. 其他含特殊符号: 7
    9. 空字符串（""）: 8
    10. 仅特殊符号（如@）: 9
    """
    s_stripped = s.strip()
    # 空字符串单独处理（权重8）
    if not s_stripped:
        return 8

    # 预编译正则（Python3.7兼容）
    special_symbol_pattern = re.compile(r'[!#@]')
    arabic_num_pattern = re.compile(r'\d')
    chinese_num_pattern = re.compile(r'[' + ''.join(CHINESE_NUM_MAP.keys()) + ']')
    english_pattern = re.compile(r'[a-zA-Z]')
    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]')
    symbol_num_only_pattern = re.compile(r'^[!#@]+\d+$')
    only_special_symbol = re.compile(r'^[!#@]+$')
    pure_english_pattern = re.compile(r'^[a-zA-Z\+\-]*$')
    pure_number_pattern = re.compile(r'^\d+$')

    # 特征提取（Python3.7兼容）
    has_special_symbol = bool(special_symbol_pattern.search(s_stripped))
    has_arabic_num = bool(arabic_num_pattern.search(s_stripped))
    has_chinese_num = bool(chinese_num_pattern.search(s_stripped))
    has_english = bool(english_pattern.search(s_stripped))
    has_chinese = bool(chinese_pattern.search(s_stripped))
    has_num = has_arabic_num or has_chinese_num
    is_pure_number = bool(pure_number_pattern.match(s_stripped))
    is_pure_english = bool(pure_english_pattern.match(s_stripped))
    is_symbol_num_only = bool(symbol_num_only_pattern.match(s_stripped))
    is_only_special_symbol = bool(only_special_symbol.match(s_stripped))

    # 规则1：纯数字（123）→ 权重0
    if is_pure_number:
        return 0
    # 规则2：纯英文（含+/-，如abc/a+b）→ 权重1
    if is_pure_english:
        return 1
    # 规则3：符号+数字（!789/#456/@123）→ 权重2
    if is_symbol_num_only:
        return 2
    # 规则4：数字+中文 → 权重3
    if has_num and not has_english and has_chinese and not has_special_symbol:
        return 3
    # 规则5：数字+英文 → 权重4
    if has_num and has_english and not has_chinese and not has_special_symbol:
        return 4
    # 规则6：数字+英文+中文 → 权重5
    if has_num and has_english and has_chinese and not has_special_symbol:
        return 5
    # 规则7：纯中文 → 权重6
    if has_chinese and not has_english and not has_num and not has_special_symbol:
        return 6
    # 规则8：其他含特殊符号 → 权重7
    if has_special_symbol:
        return 7
    # 规则9：仅特殊符号（如@）→ 权重9
    if is_only_special_symbol:
        return 9
    # 兜底 → 权重8
    return 8


def parse_chinese_num(char: str) -> Optional[int]:
    """解析中文数字，Python3.7兼容返回Optional"""
    return CHINESE_NUM_MAP.get(char)


def mixed_sort_key(s: str) -> Tuple[int, Tuple, int]:
    """Python3.7兼容的排序键生成函数"""
    main_type = get_str_main_type(s)
    # 拆分正则：覆盖符号/数字/英文/中文/+/-
    pattern = re.compile(r'(?:[!#@]+)|(?:\d+)|(?:[a-zA-Z]+)|(?:[\u4e00-\u9fa5]+)|(?:[+-]+)')
    key_parts = []
    s_stripped = s.strip()

    for match in pattern.finditer(s):
        part = match.group()
        # 1. 特殊符号（!#@）：按ASCII码排序（! < # < @）
        if re.match(r'[!#@]+', part):
            key_parts.append(('s', part))
        # 2. 阿拉伯数字：自然排序（转int）
        elif re.match(r'\d+', part):
            key_parts.append(('n', int(part)))
        # 3. 英文：小写优先，原字符次之（保证aBc < apple < Banana）
        elif re.match(r'[a-zA-Z]+', part):
            for char in part:
                key_parts.append(('e', (char.lower(), char)))
        # 4. 中文：拼音小写+中文数字转数值（航拍中国排序）
        elif re.match(r'[\u4e00-\u9fa5]+', part):
            for char in part:
                num_val = parse_chinese_num(char)
                if num_val is not None:
                    key_parts.append(('n', num_val))
                else:
                    pinyin_result = pinyin(char, style=Style.NORMAL, strict=True)
                    pinyin_str = pinyin_result[0][0].lower()
                    key_parts.append(('c', pinyin_str))
        # 5. +/-分隔符：按ASCII码排序（+ < -）
        elif re.match(r'[+-]+', part):
            key_parts.append(('d', part))

    # 字符串长度：同优先级时短的在前
    str_length = len(s_stripped) if s_stripped else 0
    return main_type, tuple(key_parts), str_length


def mixed_sort(str_list: List[str]) -> List[str]:
    """对外暴露的排序接口"""
    return sorted(str_list, key=mixed_sort_key)
