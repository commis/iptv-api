#!/usr/bin/env python
# -*- coding: utf-8 -*-
import binascii

from Crypto.Cipher import AES

# Navicat 12+/15+ 的密钥/IV
KEY = b"libcckeylibcckey"
IV = b"libcciv libcciv "


def decrypt(encrypted_hex):
    raw = binascii.unhexlify(encrypted_hex)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    plain = cipher.decrypt(raw).rstrip(b"\0").decode()
    return plain


if __name__ == "__main__":
    pwd_hex = "833E4ABBC56C89041A9070F043641E3B"
    print("明文密码：", decrypt(pwd_hex))
