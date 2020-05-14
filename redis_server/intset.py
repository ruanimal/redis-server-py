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

def intsetSearch(s: intset, value: int, pos: Opt[intptr]) -> int:
    minimal = 0
    maximum = intrev32ifbe(s.length)-1
    mid = -1
    cur = -1

    if (intrev32ifbe(s.length) == 0):
        if pos:
            pos.value = 0
        return 0
    else:
        if value > _intsetGet(s, intrev32ifbe(s.length)-1):
            if pos:
                pos.value = intrev32ifbe(s.length)
            return 0
        elif value < _intsetGet(s, 0):
            if pos:
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
        if pos:
            pos.value = mid
        return 1
    else:
        if pos:
            pos.value = minimal
        return 0


def intsetUpgradeAndAdd(s: intset, value: int) -> intset:
    curenc = intrev32ifbe(s.encoding)
    newenc = _intsetValueEncoding(value)
    length = intrev32ifbe(s.length)

    prepend = value < 0 and 1 or 0
    s.encoding = intrev32ifbe(newenc)

    while length:
        length -= 1
        _intsetSet(s, length+prepend, _intsetGetEncoded(s, length, curenc))

    if prepend:
        _intsetSet(s, 0, value)
    else:
        _intsetSet(s, intrev32ifbe(s.length), value)
    s.length = intrev32ifbe(intrev32ifbe(s.length)+1)
    return s


def intsetMoveTail(s: intset, from_: int, to: int) -> None:
    bytes_count = intrev32ifbe(s.length) - from_
    encoding = intrev32ifbe(s.encoding)
    assert encoding in INTSET_ENCS

    src = from_
    dst = to
    if encoding == INTSET_ENC_INT64:
        bytes_count *= 8
    elif encoding == INTSET_ENC_INT32:
        bytes_count *= 4
    else:
        bytes_count *= 2
    memmove(s.contents, dst, src, bytes_count)


def intsetAdd(s: intset, value: int, success: intptr) -> intset:
    valenc = _intsetValueEncoding(value)
    ptr_pos = intptr()
    ptr_pos.value = 0
    success.value = 1
    if valenc > intrev32ifbe(s.encoding):
        return intsetUpgradeAndAdd(s, value)
    else:
        if intsetSearch(s, value, ptr_pos):
            success.value = 0
            return s

        s = intsetResize(s, intrev32ifbe(s.length)+1)
        if ptr_pos.value < intrev32ifbe(s.length):
            intsetMoveTail(s, ptr_pos.value, ptr_pos.value+1)

    _intsetSet(s, ptr_pos.value, value)
    s.length = intrev32ifbe(intrev32ifbe(s.length)+1)
    return s


def intsetRemove(s: intset, value: int, success: intptr) -> intset:
    valenc = _intsetValueEncoding(value)
    success.value = 0
    pos = intptr()
    pos.value = 0

    if valenc <= intrev32ifbe(s.encoding) and intsetSearch(s, value, pos):
        length = intrev32ifbe(s.length)
        success.value = 1
        if pos.value < length - 1:
            intsetMoveTail(s, pos.value+1, pos.value)
        s = intsetResize(s, length-1)
        s.length = intrev32ifbe(length-1)
    return s


def intsetFind(s: intset, value: int) -> int:
    valenc = _intsetValueEncoding(value)
    return valenc <= intrev32ifbe(s.encoding) and intsetSearch(s, value, None)


def intsetRandom(s: intset) -> int:
    return _intsetGet(s, c_random() % intrev32ifbe(s.length))


def intsetGet(s: intset, pos: int, value: intptr) -> int:
    if pos < intrev32ifbe(s.length):
        value.value = _intsetGet(s, pos)
        return 1
    return 0


def intsetLen(s: intset) -> int:
    return intrev32ifbe(s.length)


def intsetBlobLen(s: intset) -> int:
    # sizeof(intset)+intrev32ifbe(is->length)*intrev32ifbe(is->encoding);
    # TODO(ruan.lj@foxmail.com): 检查Python中这个地方的实现.
    return intrev32ifbe(s.length) * intrev32ifbe(s.encoding)
