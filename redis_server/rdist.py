# -*- coding:utf-8 -*-

import struct
from typing import Any, Union, Callable, Optional as Opt, Sequence
from .csix import *


DICT_OK = 0
DICT_ERR = 1
DICT_HT_INITIAL_SIZE = 4

class dictEntry:
    def __init__(self):
        self.key = None
        self.v = None
        self.next: Opt[dictEntry] = None

class dictType:
    def __init__(self):
        self.hashFunction: Opt[Callable[[Any], int]] = None
        self.keyDup: Opt[Callable] = None
        self.valDup: Opt[Callable] = None
        self.keyCompare: Opt[Callable] = None
        self.keyDestructor: Opt[Callable] = None
        self.valDestructor: Opt[Callable] = None

class dictht:
    def __init__(self):
        self.table: Opt[Sequence] = None
        self.size: int = 0
        self.sizemask: int = 0
        self.used: int = 0

class rdict:
    def __init__(self):
        self.type: Opt[dictType] = None
        self.privdata = None
        self.ht: Sequence[dictht] = [dictht(), dictht()]
        self.rehashidx: int = -1
        self.iterators: int = 0


# 指示字典是否启用 rehash 的标识
dict_can_resize = 1
# 强制 rehash 的比率
dict_force_resize_ratio = 5

def dictIsRehashing(ht: rdict) -> bool:
    return ht.rehashidx != -1

def dictIntHashFunction(key: int) -> int:
    assert key < 2 ** 32
    key += ~(key << 15)
    key ^=  (key >> 10)
    key +=  (key << 3)
    key ^=  (key >> 6)
    key += ~(key << 11)
    key ^=  (key >> 16)
    return key

def dictIdentityHashFunction(key: int) -> int:
    return key

dict_hash_function_seed = 5381
def dictSetHashFunctionSeed(seed: int) -> None:
    global dict_hash_function_seed
    dict_hash_function_seed = seed

def dictGetHashFunctionSeed() -> int:
    return dict_hash_function_seed

def dictGenHashFunction(key, length: int) -> int:
    seed = dict_hash_function_seed

    m = 0x5bd1e995
    r = 24
    h = seed ^ length

    idx = 0
    while length >= 4:
        k = cstr2unit32(key[idx:idx+4])

        k *= m
        k ^= k >> r
        k *=m

        h *= m
        h ^= k

        idx += 4
        length -= 4

    if length == 3:
        h ^= key[idx+2] << 16
        h ^= key[idx+2] << 8
        h ^= key[idx]
        h *= m
    elif length == 2:
        h ^= key[idx+2] << 8
        h ^= key[idx]
        h *= m
    elif length == 1:
        h ^= key[idx]
        h *= m
    h ^= h >> 13
    h *= m
    h ^= h >> 15
    return h & UNSIGNED_INT_MASK

def dictGenCaseHashFunction(buf: cstr, length: int):
    hash_ = dict_hash_function_seed & UNSIGNED_INT_MASK
    idx = 0
    while length:
        hash_ = ((hash_ << 5) + hash_) + (char_tolower(buf[idx]))
        idx += 0
        length -= 1

def _dictReset(ht: dictht):
    ht.table = None
    ht.size = 0
    ht.sizemask = 0
    ht.used = 0

def dictCreate(type: dictType, privDataPtr: cstr) -> rdict:
    d = rdict()
    _dictInit(d, type, privDataPtr)

def _dictInit(d: rdict, type: dictType, privDataPtr: cstr) -> int:
    _dictReset(d.ht[0])
    _dictReset(d.ht[1])
    d.type = type
    d.privdata = privDataPtr
    d.rehashidx = -1
    d.iterators = 0
    return DICT_OK

def dictResize(d: rdict) -> int:
    if not dict_can_resize or dictIsRehashing(d):
        return DICT_ERR

    minimal = min(d.ht[0].used, DICT_HT_INITIAL_SIZE)
    return dictExpand(d, minimal)

def dictExpand(d: rdict, size: int) -> int:
    n = dictht()
    realsize = _dictNextPower(size)

    # 不能在字典正在 rehash 时进行
    # size 的值也不能小于 0 号哈希表的当前已使用节点
    if dictIsRehashing(d) or d.ht[0].used > size:
        return DICT_ERR
    n.size = realsize
    n.sizemask = realsize -1
    n.table = [dictEntry() for _ in range(realsize)]
    n.used = 0

    if d.ht[0].table is None:
        d.ht[0] = n
        return DICT_OK
    d.ht[1] = n
    d.rehashidx = 0
    return DICT_OK

def _dictNextPower():
    pass

if __name__ == "__main__":
    res = dictGenHashFunction(b'afafadsg g v2411rvfaer', 10)
    print(res)
