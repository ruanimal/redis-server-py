# -*- coding:utf-8 -*-

import time
import struct
from typing import Any, Union, Callable, Optional as Opt, List
from .csix import *


DICT_OK = 0
DICT_ERR = 1
DICT_HT_INITIAL_SIZE = 4
LONG_MAX = 0x7fffffffffffffff


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
        self.table: List[Any] = []
        self.size: int = 0
        self.sizemask: int = 0
        self.used: int = 0

class Dict:
    def __init__(self):
        self.type: Opt[dictType] = None
        self.privdata = None
        self.ht: List[dictht] = [dictht(), dictht()]
        self.rehashidx: int = -1
        self.iterators: int = 0


# 指示字典是否启用 rehash 的标识
dict_can_resize = 1
# 强制 rehash 的比率
dict_force_resize_ratio = 5

def dictIsRehashing(ht: Dict) -> bool:
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
    ht.table = []
    ht.size = 0
    ht.sizemask = 0
    ht.used = 0

def dictCreate(type: dictType, privDataPtr: cstr) -> Dict:
    d = Dict()
    _dictInit(d, type, privDataPtr)
    return d

def _dictInit(d: Dict, type: dictType, privDataPtr: cstr) -> int:
    _dictReset(d.ht[0])
    _dictReset(d.ht[1])
    d.type = type
    d.privdata = privDataPtr
    d.rehashidx = -1
    d.iterators = 0
    return DICT_OK

def dictResize(d: Dict) -> int:
    if not dict_can_resize or dictIsRehashing(d):
        return DICT_ERR

    minimal = min(d.ht[0].used, DICT_HT_INITIAL_SIZE)
    return dictExpand(d, minimal)

def dictExpand(d: Dict, size: int) -> int:
    n = dictht()
    realsize = _dictNextPower(size)

    # 不能在字典正在 rehash 时进行
    # size 的值也不能小于 0 号哈希表的当前已使用节点
    if dictIsRehashing(d) or d.ht[0].used > size:
        return DICT_ERR
    n.size = realsize
    n.sizemask = realsize -1
    # n.table = [dictEntry() for _ in range(realsize)]
    n.table = [None for _ in range(realsize)]
    n.used = 0

    if d.ht[0].table is None:
        d.ht[0] = n
        return DICT_OK
    d.ht[1] = n
    d.rehashidx = 0
    return DICT_OK


def dictRehash(d: Dict, n: int) -> int:
    if not dictIsRehashing(d):
        return 0

    while (n):
        n -= 1
        if d.ht[0].used == 0:
            del d.ht[0].table
            d.ht[0] = c_assignment(d.ht[1])
            _dictReset(d.ht[1])
            d.rehashidx = -1
            return 0

        assert d.ht[0].size > d.rehashidx
        while d.ht[0].table[d.rehashidx] is None:
            d.rehashidx += 1

        de = d.ht[0].table[d.rehashidx]
        while de:
            nextde = de.next
            h = dictHashKey(d, de.key) & d.ht[1].sizemask
            de.next = d.ht[1].table[h]
            d.ht[1].table[h] = de
            d.ht[0].used -= 1
            d.ht[1].used += 1
            de = nextde
        d.ht[0].table[d.rehashidx] = None
        d.rehashidx += 1
    return 1


def timeInMilliseconds() -> int:
    return int(time.time() * 1000)


def dictRehashMilliseconds(d: Dict, ms: int) -> int:
    start = timeInMilliseconds()
    rehashes = 0
    while dictRehash(d, 100):
        rehashes += 100
        if timeInMilliseconds() - start > ms:
            break
    return rehashes

def _dictRehashStep(d: Dict) -> None:
    if d.iterators == 0:
        dictRehash(d, 1)

def dictAdd(d: Dict, key, val) -> int:
    entry = dictAddRaw(d, key)
    if not entry:
        return DICT_ERR

    dictSetVal(d, entry, val)
    return DICT_OK

def dictAddRaw(d: Dict, key) -> Opt[dictEntry]:
    if dictIsRehashing(d):
        _dictRehashStep(d)

    index = _dictKeyIndex(d, key)
    if index == -1:
        return None

    ht = d.ht[1] if dictIsRehashing(d) else d.ht[0]
    entry = dictEntry()
    entry.next = ht.table[index]
    ht.table[index] = entry
    ht.used += 1
    dictSetKey(d, entry, key)
    return entry

def dictReplace(d: Dict, key, val) -> int:
    if dictAdd(d, key, val) == DICT_OK:
        return 1

    entry = dictFind(d, key)
    # auxentry = * entry
    dictSetVal(d, key, val)
    # NOTE no dictFreeVal(&auxentry) in python
    return 0

def dictReplaceRaw(d: Dict, key) -> dictEntry:
    entry = dictFind(d, key)
    return entry if entry else dictAddRaw(d, key)

def dictGenericDelete(d: Dict, key, nofree: int) -> int:
    if d.ht[0].size == 0:
        return DICT_ERR

    if dictIsRehashing(d):
        _dictRehashStep(d)

    h = dictHashKey(d, key)
    for table in range(2):
        idx = h & d.ht[table].sizemask
        he = d.ht[table].table[idx]
        prev_he = None

        while he:
            if dictCompareKeys(d, key, he.key):
                if prev_he:
                    prev_he.next = he.next
                else:
                    d.ht[table].table[idx] = he.next

                if not nofree:  # NOTE no need in python
                    dictFreeKey(d, he)
                    dictFreeVal(d, he)

                del he
                d.ht[table].used -= 1
                return DICT_OK

            prev_he = he
            he = he.next

        if not dictIsRehashing(d):
            break

    return DICT_ERR


def dictDelete(ht: Dict, key) -> int:
    return dictGenericDelete(ht, key, 0)


def dictDeleteNoFree(ht: Dict, key) -> int:
    return dictGenericDelete(ht, key, 1)


def _dictNextPower(size: int) -> int:
    i = DICT_HT_INITIAL_SIZE
    if size >= LONG_MAX:
        return LONG_MAX
    while True:
        if i >= size:
            return i
        i *= 2

def dictHashKey():
    pass

def _dictKeyIndex() -> int:
    pass

def dictSetKey():
    pass

def dictSetVal(d: Dict, entry: dictEntry, val) -> None:
    if d.type and d.type.valDup:
        entry.v.val = d.type.valDup(d.privdata, val)
    else:
        entry.v.val = val

def dictFind():
    pass

def dictCompareKeys():
    pass


def donothing(*args, **kw) -> None:
    pass

dictFreeKey = donothing
dictFreeVal = donothing

if __name__ == "__main__":
    res = dictGenHashFunction(b'afafadsg g v2411rvfaer', 10)
    print(res)
    d = Dict()
    d.ht[0] = dictht()
