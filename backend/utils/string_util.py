#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @time   : 1/28/26
# @author : Brian
# @license: (C) Copyright 2022-2026
from datetime import datetime


def get_xml_cvt_string(data_str) -> str:
    return data_str.replace('&', '&amp;').replace(
        '<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')


def seconds_to_time_str(timestamp_seconds):
    """秒级时间戳转%Y%m%d%H%M%S格式字符串（本地时区）"""
    try:
        return datetime.fromtimestamp(timestamp_seconds).strftime("%Y%m%d%H%M%S")
    except (ValueError, TypeError, OSError):
        return ""


def ms2time_str(ms_timestamp):
    """毫秒级时间戳转%Y%m%d%H%M%S格式字符串（本地时区）"""
    try:
        return datetime.fromtimestamp(ms_timestamp / 1000).strftime("%Y%m%d%H%M%S")
    except (ValueError, TypeError, OSError):
        return ""
