# -*- coding:utf-8 -*-

from typing import Any, Union, Callable, Optional as Opt, Sequence


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
        self.table: Sequence = []
        self.size: int = 0
        self.sizemask: int = 0
        self.used: int = 0

class rdict:
    def __init__(self):
        self.type: Opt[dictType] = None
        self.privdata = None
        self.ht: Opt[Sequence[dictht]] = None
        self.rehashidx: int = -1
        self.iterators: int = 0


# 指示字典是否启用 rehash 的标识
dict_can_resize = 1
# 强制 rehash 的比率
dict_force_resize_ratio = 5

def dictIntHashFunction(key: int) -> int:
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
    dict_hash_function_seed = seed

def dictGetHashFunctionSeed() -> int:
    return dict_hash_function_seed

def dictGenHashFunction(key, length: int) -> int:
    pass
