import struct
import locale
from typing import Union
from copy import copy as c_assignment   # 模拟c语言赋值, 拷贝所有成员
from random import randint


__all__ = [
    'cstr',
    'NUL',
    'UINT_MASK',
    'ULONG_MASK',
    'strlen',
    'memcmp',
    'memcpy',
    'cstr2uint32',
    'cstr2int64',
    'cstr2uint64',
    'char_tolower',
    'c_assignment',
    'zfree',
    'c_random',
    'ptr2long',
    'strcoll',
]

cstr = Union[bytearray, bytes]

# C语言 \0
NUL = 0
UINT_MASK = 2 ** 32 - 1
ULONG_MASK = 2 ** 64 - 1

cstr2uint32 = lambda data: struct.unpack('=I', data)[0]
cstr2uint64 = lambda data: struct.unpack('=Q', data)[0]
cstr2int64 = lambda data: struct.unpack('=q', data)[0]
c_random = lambda: randint(0, 2147483647)

def zfree(ptr) -> None:
    del ptr

def strlen(string: cstr) -> int:
    res = 0
    for i in string:
        if i == NUL:
            break
        res += 1
    return res


def memcmp(s1: cstr, s2: cstr, length: int) -> int:
    minlen = min(len(s1), len(s2), length)
    for i in range(minlen):
        if s1[i] > s2[i]:
            return 1
        elif s1[i] < s2[i]:
            return -1
    return 0

def memcpy(dest: bytearray, src: cstr, length: int) -> None:
    dest[:length] = src[:length]

def char_tolower(char: int):
    tmp = bytearray()
    tmp.append(char)
    return tmp.lower()[0]

def ptr2long(ptr) -> int:
    assert id(ptr) <= ULONG_MASK
    return id(ptr)

def strcoll(a: cstr, b: cstr):
    return locale.strcoll(a.decode(), b.decode())
