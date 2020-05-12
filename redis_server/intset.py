from typing import Any, Union, Callable, Optional as Opt, List
from .csix import *
from .endianconv import intrev32ifbe

# intset 的编码方式
INTSET_ENC_INT16 = 2  # (sizeof(int16_t))
INTSET_ENC_INT32 = 4  # (sizeof(int32_t))
INTSET_ENC_INT64 = 8  # (sizeof(int64_t))

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

def intsetNew() -> intset:
    s = intset()
    s.encoding = intrev32ifbe(INTSET_ENC_INT16)
    s.length = 0
    return s
