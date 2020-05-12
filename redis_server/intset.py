from typing import Any, Union, Callable, Optional as Opt, List
from .csix import *
from .endianconv import intrev32ifbe

# intset 的编码方式
INTSET_ENC_INT16 = 2  # (sizeof(int16_t))
INTSET_ENC_INT32 = 4  # (sizeof(int32_t))
INTSET_ENC_INT64 = 8  # (sizeof(int64_t))
INTSET_ENCS = {INTSET_ENC_INT16, INTSET_ENC_INT32, INTSET_ENC_INT64}

class intptr:
    def __init__(self):
        self.value: int = 0

class intset:
    def __init__(self):
        self.encoding: int = 0
        self.length: int = 0
        self.contents: bytearray = bytearray()

def _intsetValueEncoding(v: int) -> int:
    assert INT64_MIN <= v <= INT64_MAX
    if v < INT32_MIN or v > INT32_MAX:
        return INTSET_ENC_INT64
    elif v < INT16_MIN or v > INT16_MAX:
        return INTSET_ENC_INT32
    else:
        return INTSET_ENC_INT16

def _intsetGetEncoded(s: intset, pos: int, enc: int) -> int:
    assert enc in INTSET_ENCS
    if enc == INTSET_ENC_INT64:
        return cstr2int(s.contents[pos:pos+8], 'int64')
    elif enc == INTSET_ENC_INT32:
        return cstr2int(s.contents[pos:pos+4], 'int32')
    else:
        return cstr2int(s.contents[pos:pos+2], 'int16')

def _intsetGet(s: intset, pos: int) -> int:
    return _intsetGetEncoded(s, pos, intrev32ifbe(s.encoding))

def _intsetSet(s: intset, pos: int, value: int) -> None:
    encoding = intrev32ifbe(s.encoding)
    if encoding == INTSET_ENC_INT64:
        s.contents[pos:pos+8] = int2cstr(value, 'int64')
    elif encoding == INTSET_ENC_INT32:
        s.contents[pos:pos+4] = int2cstr(value, 'int32')
    else:
        s.contents[pos:pos+2] = int2cstr(value, 'int16')

def intsetNew() -> intset:
    s = intset()
    s.encoding = intrev32ifbe(INTSET_ENC_INT16)
    s.length = 0
    return s

def intsetResize(s: intset, length: int) -> intset:
    size = length * intrev32ifbe(s.encoding)
    # zrealloc to new size
    s.contents.extend(NUL for _ in range(size-len(s.contents)))
    return s

def intsetSearch(s: intset, value: int, pos: intptr) -> int:
    minimal = 0
    maximum = intrev32ifbe(s.length)-1
    mid = -1
    cur = -1

    if (intrev32ifbe(s.length) == 0):
        pos.value = 0
        return 0
    else:
        if value > _intsetGet(s, intrev32ifbe(s.length)-1):
            pos.value = intrev32ifbe(s.length)
            return 0
        elif value < _intsetGet(s, 0):
            pos.value = 0
            return 0

    while maximum >= minimal:
        mid = (minimal + maximum) // 2
        cur = _intsetGet(s, mid)
        if value > cur:
            minimal = mid + 1
        elif value < cur:
            maximum = mid - 1
        else:
            break

    if value == cur:
        pos.value = mid
        return 1
    else:
        pos.value = minimal
        return 0

