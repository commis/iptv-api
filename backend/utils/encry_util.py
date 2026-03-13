#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @time   : 1/22/26
# @author : Brian
# @license: (C) Copyright 2022-2026
import hashlib


def getStringMD5(input_str):
    md5 = hashlib.md5()
    byte_str = input_str.encode('utf-8')
    md5.update(byte_str)
    return md5.hexdigest()
