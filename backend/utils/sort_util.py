import re

from pypinyin import pinyin, Style


def mixed_sort_key(s):
    """
    混合排序键：同时支持数字自然排序和汉字拼音排序
    1. 按字母/符号顺序（ASCII码）
    2. 按数字大小（自然排序）
    3. 按汉字拼音（小写）
    """
    # 定义正则模式：字母/符号、数字、汉字
    pattern = re.compile(r'([a-zA-Z]+|[^\w\s]+)|(\d+)|([\u4e00-\u9fa5]+)')
    key_parts = []

    for match in pattern.finditer(s):
        alpha_part, num_part, chinese_part = match.groups()

        if alpha_part:
            # 字母/符号部分：转小写后作为元组
            key_parts.append(('a', alpha_part.lower()))
        elif num_part:
            # 数字部分：转为整数
            key_parts.append(('n', int(num_part)))
        elif chinese_part:
            # 汉字部分：转换为拼音列表
            pinyin_list = pinyin(chinese_part, style=Style.NORMAL, strict=False)
            # 拼接拼音并转小写
            pinyin_str = ''.join([p[0].lower() for p in pinyin_list])
            key_parts.append(('c', pinyin_str))

    return tuple(key_parts)
