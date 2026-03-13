#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @time   : 4/25/25
# @author : Brian
# @license: (C) Copyright 2022-2026

# 个人身份证件采用18位校验码算法： MOD 11-2
# 数据空间主体身份采用32校验码算法： MOD 37-2

def convert_checksum(check_value, modulus=37):
    if modulus == 11:
        cv = (12 - check_value) % 11
        return 'X' if cv == 10 else str(cv)
    elif modulus == 37:
        remainder = (1 - check_value) % modulus
        return '*' if remainder == 36 else str(remainder) if remainder < 10 else chr(ord('A') + remainder - 10)
    else:
        raise ValueError(f"不支持的模数 {modulus}")


# 18位ID校验位映射表
CHECKSUM_MAP_MOD_11 = {r: convert_checksum(r, 11) for r in range(11)}
print(f"ID校验位映射表: len={len(CHECKSUM_MAP_MOD_11)}, {CHECKSUM_MAP_MOD_11}")

# 32位ID校验位映射表
CHECKSUM_MAP_MOD_37 = {r: convert_checksum(r, 37) for r in range(33)}
print(f"ID校验位映射表: len={len(CHECKSUM_MAP_MOD_37)}, {CHECKSUM_MAP_MOD_37}")


def get_value(char):
    return int(char) if char.isdigit() else ord(char.upper()) - ord('A') + 10


def calculate_checksum_recursive(input_str, modulus=37, r=2):
    front_str = input_str[:-1]
    remainder = 0
    for char in front_str:
        value = get_value(char)
        remainder = (remainder + value) * r % modulus
    return convert_checksum(remainder, modulus)


def calculate_checksum_polynomial(input_str, modulus=37, r=2):
    source_size = len(input_str) - 1
    remainder = 0
    total = 0
    for i in range(source_size):
        char = input_str[i]
        value = get_value(char)
        pos = source_size - i + 1
        weight = pow(r, pos - 1, modulus)
        # print(f"pos={pos}, weight={weight}, char={char}, value={value}")
        remainder = (remainder + value * weight) % modulus
    return convert_checksum(remainder, modulus)


def validate_checksum(source_str, checksum_value, checksum_value1):
    front_size = len(source_str) - 1
    target_str = source_str[:front_size] + checksum_value
    target_str1 = source_str[:front_size] + checksum_value1
    result = "✅ 核验正确" if source_str == target_str else "❌ 核验错误"
    result1 = "✅ 核验正确" if source_str == target_str1 else "❌ 核验错误"
    print(f"输入标识：{source_str}，校验位：{source_str[-1]}，"
          f"纯系统验证：[递归：{checksum_value}，{result}；多项式：{checksum_value1}，{result1}]")


def validate_checksum_test(input_string, m, r=2):
    checksum = calculate_checksum_recursive(input_string, m, r)
    checksum1 = calculate_checksum_polynomial(input_string, m, r)
    validate_checksum(input_string, checksum, checksum1)


if __name__ == "__main__":
    # MOD 11
    validate_checksum_test("622421196903065015", 11)
    # validate_checksum_test("07940", 11)
    # validate_checksum_test("079X", 11)

    # MOD 37
    validate_checksum_test("291350182MAC4HLYX9A3501B574U6Q5N", 37)

    # for i in range(0, 33):
    #     result = convert_checksum(i, 37)
    #     print(f"i={i}, result={result}")
