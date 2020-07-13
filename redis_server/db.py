import typing
from typing import List, Callable, Optional as Opt, Tuple
from .rdict import rDict, dictGenHashFunction, dictType
from .sds import sds, sdslen
from .csix import memcmp, timeval
from .robject import redisObject, dictRedisObjectDestructor
from .config import *
from .rdict import *
from .util import get_server

if typing.TYPE_CHECKING:
    from .redis import RedisClient

def dictSdsHash(key: sds) -> int:
    return dictGenHashFunction(key, sdslen(key))

def dictObjHash(key: redisObject) -> int:
    return dictGenHashFunction(key.ptr, sdslen(key.ptr))

def dictSdsKeyCompare(privdata, key1: sds, key2: sds) -> int:
    from .sds import sdslen
    l1 = sdslen(key1)
    l2 = sdslen(key2)
    if l1 != l2:
        return 0
    return memcmp(key1.buf, key2.buf, l1) == 0

def dictSdsDestructor(privdata, val):
    pass

def dictObjKeyCompare(*args):
    pass

def dictListDestructor(*args):
    pass

def dictEncObjHash(*args):
    pass

def dictEncObjKeyCompare(*args):
    pass

dbDictType = dictType()
dbDictType.hashFunction = dictSdsHash
dbDictType.keyDup = None
dbDictType.valDup = None
dbDictType.keyCompare = dictSdsKeyCompare
dbDictType.keyDestructor = dictSdsDestructor
dbDictType.valDestructor = dictRedisObjectDestructor

keyptrDictType = dictType()
keyptrDictType.hashFunction = dictSdsHash
keyptrDictType.keyDup = None
keyptrDictType.valDup = None
keyptrDictType.keyCompare = dictSdsKeyCompare
keyptrDictType.keyDestructor = None
keyptrDictType.valDestructor = None

keylistDictType = dictType()
keylistDictType.hashFunction = dictObjHash
keylistDictType.keyDup = None
keylistDictType.valDup = None
keylistDictType.keyCompare = dictObjKeyCompare
keylistDictType.keyDestructor = dictRedisObjectDestructor
keylistDictType.valDestructor = dictListDestructor

setDictType = dictType()
setDictType.hashFunction = dictEncObjHash
setDictType.keyDup = None
setDictType.valDup = None
setDictType.keyCompare = dictEncObjKeyCompare
setDictType.keyDestructor = dictRedisObjectDestructor
setDictType.valDestructor = None

REDIS_EVICTION_POOL_SIZE = 16
class evictionPoolEntry:
    def __init__(self):
        self.idle: int = 0
        self.key: sds = None

def evictionPoolAlloc() -> List[evictionPoolEntry]:
    return [evictionPoolEntry() for _ in range(REDIS_EVICTION_POOL_SIZE)]

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

def getExpire(db: RedisDB, key: redisObject) -> int:
    if dictSize(db.expires) == 0:
        return -1
    de = dictFind(db.expires, key.ptr)
    if de == None:
        return -1
    assert dictFind(db.dict, key.ptr) != None
    return dictGetSignedIntegerVal(de)   # type: ignore

def propagateExpire(db: RedisDB, key: redisObject):
    """将过期时间传播到附属节点和 AOF 文件。"""
    pass

def notifyKeyspaceEvent(type: int, event: str, key: redisObject, dbid: int) -> None:
    """发送事件通知"""
    # NOTE: 暂不实现
    pass

def dbDelete(db: RedisDB, key: redisObject) -> int:
    if dictSize(db.expires) > 0:
        dictDelete(db.expires, key.ptr)
    if dictDelete(db.dict, key.ptr) == DICT_OK:
        return 1
    else:
        return 0

def expireIfNeeded(db: RedisDB, key: redisObject) -> int:
    server = get_server()
    when = getExpire(db, key)
    if when < 0:
        return 0
    if server.loading:
        return 0
    now = timeval.from_datetime().mstime
    if now <= when:
        return 0
    server.stat_expiredkeys += 1
    propagateExpire(db, key)
    notifyKeyspaceEvent(REDIS_NOTIFY_EXPIRED, 'expired', key, db.id)
    return dbDelete(db, key)

def lookupKey(db: RedisDB, key: redisObject) -> Opt[redisObject]:
    from .redis import LRUClock
    server = get_server()
    de = dictFind(db.dict, key.ptr)
    if de:
        val = dictGetVal(de)
        if server.rdb_child_pid == -1 and server.aof_child_pid == -1:
            val.lru = LRUClock()
        return val
    else:
        return None

def lookupKeyRead(db: RedisDB, key: redisObject) -> Opt[redisObject]:
    expireIfNeeded(db, key)
    val = lookupKey(db, key)
    server = get_server()
    if val == None:
        server.stat_keyspace_misses += 1
    else:
        server.stat_keyspace_hits += 1
    return val

def lookupKeyReadOrReply(c: 'RedisClient', key: redisObject, reply: redisObject) -> Opt[redisObject]:
    from .networking import addReply
    o = lookupKeyRead(c.db, key)
    if not o:
        addReply(c, reply)
    return o
