# -*- coding:utf-8 -*-

import time
import struct
from typing import Any, Union, Callable, Optional as Opt, List
from .csix import *


DICT_OK = 0
DICT_ERR = 1
DICT_HT_INITIAL_SIZE = 4
LONG_MAX = 0x7fffffffffffffff

class dictEntryVal:
    def __init__(self, val=None):
        self.val = val

    @property
    def u64(self):
        return cstr2uint64(self.val)

    @property
    def s64(self):
        return cstr2int64(self.val)

class dictEntry:
    def __init__(self):
        self.key = None
        self.v: dictEntryVal = dictEntryVal()
        self.next: Opt[dictEntry] = None

class dictType:
    def __init__(self):
        self.hashFunction: Callable[[Any], int] = None
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
        self.type: dictType = None
        self.privdata = None
        self.ht: List[dictht] = [dictht(), dictht()]
        self.rehashidx: int = -1
        self.iterators: int = 0

class dictIterator:
    def __init__(self):
        self.d: Dict = None
        self.table: int = 0
        self.index: int = -1
        self.safe: int = 0
        self.entry: Opt[dictEntry] = None
        self.nextEntry: Opt[dictEntry] = None
        self.fingerprint: int = 0


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
        k = cstr2uint32(key[idx:idx+4])

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

def dictReplaceRaw(d: Dict, key) -> Opt[dictEntry]:
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


def _dictClear(d: Dict, ht: dictht, callback: Opt[Callable]) -> int:
    i = 0
    while i < ht.size and ht.used > 0:
        i += 1
        if callback and ((i & 65535) == 0):
            callback(d.privdata)

        he = ht.table[i]
        if he is None:
            continue

        while he:
            next_he = he.next
            dictFreeKey(d, he)
            dictFreeVal(d, he)
            zfree(he)
            ht.used -= 1
            he = next_he

    zfree(ht.table)
    _dictReset(ht)
    return DICT_OK


def dictRelease(d: Dict) -> None:
    _dictClear(d, d.ht[0], None)
    _dictClear(d, d.ht[1], None)
    zfree(d)


def dictFind(d: Dict, key) -> Opt[dictEntry]:
    if d.ht[0].size == 0:
        return None

    if dictIsRehashing(d):
        _dictRehashStep(d)

    h = dictHashKey(d, key)
    for table in range(2):
        idx = h & d.ht[table].sizemask
        he = d.ht[table].table[idx]
        while he:
            if dictCompareKeys(d, key, he.key):
                return he
            he = he.next
        if not dictIsRehashing(d):
            return None
    return None


def dictFetchValue(d: Dict, key):
    he = dictFind(d, key)
    return he and dictGetVal(he) or None


def dictFingerprint(d: Dict) -> int:
    integers = [
        id(d.ht[0].table),   # c中是table的地址
        d.ht[0].size,
        d.ht[0].used,
        id(d.ht[1].table),
        d.ht[1].size,
        d.ht[1].used,
    ]

    hash_val = 0
    for j in range(6):
        hash_val += integers[j]
        hash_val = (~hash_val) + (hash_val << 21)
        hash_val = hash_val ^ (hash_val >> 24)
        hash_val = (hash_val + (hash_val << 3)) + (hash_val << 8)
        hash_val = hash_val ^ (hash_val >> 14)
        hash_val = (hash_val + (hash_val << 2)) + (hash_val << 4)
        hash_val = hash_val ^ (hash_val >> 28)
        hash_val = hash_val + (hash_val << 31)
    return hash_val


def dictGetIterator(d: Dict) -> dictIterator:
    it = dictIterator()
    it.d = d
    return it


def dictGetSafeIterator(d: Dict) -> dictIterator:
    it = dictGetIterator(d)
    it.safe = 1
    return it


def dictNext(it: dictIterator) -> Opt[dictEntry]:
    while 1:
        if it.entry is None:
            ht = it.d.ht[it.table]
            if it.index == -1 and it.table == 0:
                if it.safe:
                    it.d.iterators += 1
                else:
                    it.fingerprint = dictFingerprint(it.d)

            it.index += 1
            if it.index > ht.size:
                if dictIsRehashing(it.d) and it.table == 0:
                    it.table += 1
                    it.index = 0
                    ht = it.d.ht[1]
                else:
                    break
            it.entry = ht.table[it.index]
        else:
            it.entry = it.nextEntry
        if it.entry:
            it.nextEntry = it.entry.next
            return it.entry
    return None


def dictReleaseIterator(it: dictIterator) -> None:
    if not (it.index == -1 and it.table == 0):
        if it.safe:
            it.d.iterators -= 1
        else:
            assert it.fingerprint == dictFingerprint(it.d)
    zfree(it)


def dictGetRandomKey(d: Dict) -> Opt[dictEntry]:
    if dictSize(d) == 0:
        return None

    if dictIsRehashing(d):
        _dictRehashStep(d)

    if dictIsRehashing(d):
        while True:
            h = c_random() % (d.ht[0].size + d.ht[1].size)
            he = (h >= d.ht[0].size) and d.ht[1].table[h - d.ht[0].size] or d.ht[0].table[h]
            if he:
                break
    else:
        while True:
            h = c_random() & d.ht[0].sizemask
            he = d.ht[0].table[h]
            if he:
                break

    listlen = 0
    orighe = he
    while he:
        he = he.next
        listlen += 1
    listlen = c_random() % listlen
    he = orighe
    while listlen:
        listlen -= 1
        he = he.next
    return he


def dictGetRandomKeys(d: Dict, des: List[dictEntry], count: int) -> int:
    stored = 0
    if dictSize(d) < count:
        count = dictSize(d)

    while stored < count:
        for j in range(2):
            i = c_random() & d.ht[j].sizemask
            size = d.ht[j].size
            while size:
                size -= 1
                he = d.ht[j].table[i]
                while he:
                    des.append(he)
                    he = he.next
                    stored += 1
                    if stored == count:
                        return stored
                i = (i + 1) & d.ht[j].sizemask
            assert dictIsRehashing(d) != 0
    return stored


def rev(v: int) -> int:
    bits = '{:0>64b}'.format(v)
    return int(bits[::-1], 2)


def dictScan(d: Dict, v: int, fn: Callable, privdata) -> int:
    if dictSize(d) == 0:
        return 0
    if not dictIsRehashing(d):
        t0 = d.ht[0]
        m0 = t0.sizemask
        de = t0.table[v & m0]
        while de:
            fn(privdata, de)
            de = de.next
    else:
        t0 = d.ht[0]
        t1 = d.ht[1]
        if t0.size > t1.size:
            t0, t1 = t1, t0
        m0 = t0.sizemask
        m1 = t1.sizemask
        while de:
            fn(privdata, de)
            de = de.next
        while True:
            de = t1.table[v & m1]
            while de:
                fn(privdata, de)
                de = de.next
            v = (((v | m0) + 1) & ~m0) | (v & m0)
            if not (v & (m0 ^ m1)):
                break
    v |= ~m0
    v = rev(v)
    v += 1
    v = rev(v)
    return v


def _dictExpandIfNeeded(d: Dict) -> int:
    if dictIsRehashing(d):
        return DICT_OK
    if d.ht[0].size == 0:
        return dictExpand(d, DICT_HT_INITIAL_SIZE)
    if (d.ht[0].used >= d.ht[0].size and
        (dict_can_resize or d.ht[0].used // d.ht[0].size > dict_force_resize_ratio)):
        return dictExpand(d, d.ht[0].used * 2)
    return DICT_OK


def _dictNextPower(size: int) -> int:
    i = DICT_HT_INITIAL_SIZE
    if size >= LONG_MAX:
        return LONG_MAX
    while True:
        if i >= size:
            return i
        i *= 2


def _dictKeyIndex(d: Dict, key) -> int:
    """返回空闲的索引位置"""

    if _dictExpandIfNeeded(d) == DICT_ERR:
        return -1
    h = dictHashKey(d, key)
    for table in range(2):
        idx = h & d.ht[table].sizemask
        he = d.ht[table].table[idx]
        while he:
            if dictCompareKeys(d, key, he.key):
                return -1
            he = he.next
        if not dictIsRehashing(d):
            break
    return idx


def dictEmpty(d: Dict, callback: Callable) -> None:
    _dictClear(d, d.ht[0], callback)
    _dictClear(d, d.ht[1], callback)
    d.rehashidx = -1
    d.iterators = 0


def dictEnableResize() -> None:
    global dict_can_resize
    dict_can_resize = 1


def dictDisableResize() -> None:
    global dict_can_resize
    dict_can_resize = 0


def dictHashKey(d: Dict, key) -> int:
    return d.type.hashFunction(key)


def dictSetKey(d: Dict, entry: dictEntry, key) -> None:
    if d.type and d.type.keyDup:
        entry.key = d.type.keyDup(d.privdata, key)
    else:
        entry.key = key


def dictSetVal(d: Dict, entry: dictEntry, val) -> None:
    if d.type and d.type.valDup:
        entry.v.val = d.type.valDup(d.privdata, val)
    else:
        entry.v.val = val


def dictGetVal(he: dictEntry):
    return he.v.val


def dictCompareKeys(d: Dict, key1, key2):
    if d.type and d.type.keyCompare:
        return d.type.keyCompare(d.privdata, key1, key2)
    else:
        return key1 == key2


def dictSize(d: Dict) -> int:
    return d.ht[0].used + d.ht[1].used


def donothing(*args, **kw) -> None:
    pass

dictFreeKey = donothing
dictFreeVal = donothing

if __name__ == "__main__":
    res = dictGenHashFunction(b'afafadsg g v2411rvfaer', 10)
    print(res)
    d = Dict()
    d.ht[0] = dictht()
    print(rev(5))
