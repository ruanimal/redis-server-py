from typing import Union
import struct

__all__ = [
    'cstr',
    'NUL',
    'UNSIGNED_INT_MASK',
    'strlen',
    'memcmp',
    'cstr2unit32',
    'char_tolower',
]

cstr = Union[bytearray, bytes]

# C语言 \0
NUL = 0
UNSIGNED_INT_MASK = 2 ** 32 - 1

cstr2unit32 = lambda data: struct.unpack('=I', data)[0]

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

def char_tolower(char: int):
    tmp = bytearray()
    tmp.append(char)
    return tmp.lower()[0]
