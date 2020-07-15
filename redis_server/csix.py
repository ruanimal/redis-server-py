import struct
import locale
from datetime import datetime
from typing import Union
from copy import copy as c_assignment   # 模拟c语言赋值, 拷贝所有成员
from random import randint


__all__ = [
    'cstr',
    'NUL',
    'UINT_MASK',
    'ULONG_MASK',
    'LONG_MIN',
    'LONG_MAX',
    'INT64_MAX',
    'INT64_MIN',
    'INT32_MAX',
    'INT32_MIN',
    'INT16_MAX',
    'INT16_MIN',
    'INT8_MAX',
    'INT8_MIN',
    'UINT16_MAX',
    'UCHAR_MAX',
    'strlen',
    'memcmp',
    'memcpy',
    'memmove',
    'cstr2uint32',
    'cstr2int64',
    'cstr2uint64',
    'char_tolower',
    'c_assignment',
    'zfree',
    'c_random',
    'ptr2long',
    'strcoll',
    'int2cstr',
    'cstr2int',
    'intptr',
    'cstrptr',
    'timeval',
]

cstr = Union[bytearray, bytes]

# C语言 \0
NUL = 0
UINT_MASK = 2 ** 32 - 1
ULONG_MASK = 2 ** 64 - 1
INT64_MAX = 2 ** 63 - 1
INT64_MIN = -INT64_MAX - 1
INT32_MAX = 2 ** 31 - 1
INT32_MIN = -INT32_MAX - 1
INT16_MAX = 2 ** 15 - 1
INT16_MIN = -INT16_MAX - 1
INT8_MAX = 2 ** 7 - 1
INT8_MIN = -INT8_MAX - 1
LONG_MIN = INT64_MIN
LONG_MAX = INT64_MAX

UINT16_MAX = 2 ** 16 - 1
UCHAR_MAX = 255

cstr2uint32 = lambda data: struct.unpack('=I', data)[0]
cstr2uint64 = lambda data: struct.unpack('=Q', data)[0]
cstr2int64 = lambda data: struct.unpack('=q', data)[0]
c_random = lambda: randint(0, 2147483647)

pack_type_map = {
    'int8': 'b',
    'int16': 'h',
    'int32': 'i',
    'int64': 'q',
    'uint8': 'B',
    'uint16': 'H',
    'uint32': 'I',
    'uint64': 'Q',
}

def int2cstr(v: int, int_type: str) -> bytes:
    return struct.pack('=' + pack_type_map[int_type], v)

def cstr2int(buf: cstr, int_type: str) -> int:
    return struct.unpack('=' + pack_type_map[int_type], buf)[0]

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

def memmove(buf: bytearray, dest_pos: int, src_pos: int, length: int) -> None:
    buf[dest_pos:dest_pos+length] = buf[src_pos:src_pos+length]

def char_tolower(char: int):
    tmp = bytearray()
    tmp.append(char)
    return tmp.lower()[0]

def ptr2long(ptr) -> int:
    assert id(ptr) <= ULONG_MASK
    return id(ptr)

def strcoll(a: cstr, b: cstr):
    return locale.strcoll(a.decode(), b.decode())

class intptr:
    def __init__(self, value=0):
        self.value: int = value

class cstrptr:
    def __init__(self, buf: bytearray, pos=0):
        self.buf = buf
        self.pos = pos

    def new(self, pos) -> 'cstrptr':
        return cstrptr(self.buf, pos)

    def __eq__(self, other) -> bool:
        return self.buf is other.buf and self.pos == other.pos

class timeval:
    def __init__(self):
        self.tv_sec: int = 0
        self.tv_usec: int = 0

    @property
    def time(self):
        return self.tv_sec + (self.tv_usec // 1000000)

    @property
    def mstime(self):
        return self.time * 1000 + self.tv_usec // 1000

    @property
    def ustime(self):
        return self.time * 1000000 + self.tv_usec

    @classmethod
    def from_datetime(cls, dt: datetime=None):
        """create timeval from datetime"""
        if dt is None:
            dt = datetime.now()
        tv = cls()
        tv.tv_sec = int(dt.timestamp())
        tv.tv_usec = dt.microsecond
        return tv
