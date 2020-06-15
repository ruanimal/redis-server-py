from typing import List, Callable, Optional as Opt, Tuple
from .rdict import rDict, dictGenHashFunction, dictType
from .sds import sds, sdslen
from .csix import memcmp
from .robject import redisObject, dictRedisObjectDestructor

def dictSdsHash(key: sds) -> int:
    return dictGenHashFunction(key, sdslen(key))

def dictSdsKeyCompare(privdata, key1: sds, key2: sds) -> int:
    from .sds import sdslen
    l1 = sdslen(key1)
    l2 = sdslen(key2)
    if l1 != l2:
        return 0
    return memcmp(key1.buf, key2.buf, l1) == 0

def dictSdsDestructor(privdata, val):
    pass

dbDictType = dictType()
dbDictType.hashFunction = dictSdsHash
dbDictType.keyDup = None
dbDictType.valDup = None
dbDictType.keyCompare = dictSdsKeyCompare
dbDictType.keyDestructor = dictSdsDestructor
dbDictType.valDestructor = dictRedisObjectDestructor


class evictionPoolEntry:
    def __init__(self):
        self.idle: int = 0
        self.key: sds = None

class RedisDB:
    def __init__(self):
        # // 数据库键空间，保存着数据库中的所有键值对
        self.dict: rDict = None
        # // 键的过期时间，字典的键为键，字典的值为过期事件 UNIX 时间戳
        self.expires: rDict = None
        # // 正处于阻塞状态的键
        self.blocking_keys: rDict = None
        # // 可以解除阻塞的键
        self.ready_keys: rDict = None
        # // 正在被 WATCH 命令监视的键
        self.watched_keys: rDict = None
        # /* Eviction pool of keys */
        self.eviction_pool: List[evictionPoolEntry] = None
        self.id: int = 0
        # /* Average TTL, just for stats */
        self.avg_ttl: int = 0
