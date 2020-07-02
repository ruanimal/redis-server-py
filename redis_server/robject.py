from typing import List, Callable, Optional as Opt, Tuple
from .sds import sdslen, sdsnewlen
from .util import ll2string
from .csix import ptr2long, strcoll, memcmp, cstr

REDIS_LRU_BITS = 24

# 对象类型
REDIS_STRING = 0
REDIS_LIST = 1
REDIS_SET = 2
REDIS_ZSET = 3
REDIS_HASH = 4

# 对象编码
REDIS_ENCODING_RAW = 0   #     /* Raw representation */
REDIS_ENCODING_INT = 1   #     /* Encoded as integer */
REDIS_ENCODING_HT = 2   #      /* Encoded as hash table */
REDIS_ENCODING_ZIPMAP = 3   #  /* Encoded as zipmap */
REDIS_ENCODING_LINKEDLIST = 4   # /* Encoded as regular linked list */
REDIS_ENCODING_ZIPLIST = 5   # /* Encoded as ziplist */
REDIS_ENCODING_INTSET = 6   #  /* Encoded as intset */
REDIS_ENCODING_SKIPLIST = 7   #  /* Encoded as skiplist */
REDIS_ENCODING_EMBSTR = 8   #  /* Embedded sds string encoding */

class redisObject:
    def __init__(self):
        self.type: int = 0
        self.encoding: int = 0
        self.lru: int = REDIS_LRU_BITS
        self.refcount: int = 0
        self.ptr = None

robj = redisObject


def createObject(obj_type: int, ptr) -> robj:
    from .redis import LRUClock
    o = redisObject()
    o.type = obj_type
    o.encoding = REDIS_ENCODING_RAW
    o.ptr = ptr
    o.refcount = 1
    o.lru = LRUClock()
    return o


def createRawStringObject(ptr: cstr, length: int) -> robj:
    return createObject(REDIS_STRING, sdsnewlen(ptr, length))

def createEmbeddedStringObject(ptr: cstr, length: int) -> robj:
    o = createRawStringObject(ptr, length)
    o.encoding = REDIS_ENCODING_EMBSTR
    return o

REDIS_ENCODING_EMBSTR_SIZE_LIMIT = 39
def createStringObject(ptr: cstr, length: int) -> robj:
    if (len <= REDIS_ENCODING_EMBSTR_SIZE_LIMIT):
        return createEmbeddedStringObject(ptr, length)
    else:
        return createRawStringObject(ptr, length)


def decrRefCount(o: redisObject) -> None:
    assert o.refcount > 0
    if o.refcount == 1:
        # NOTE: collect object
        o.refcount = 0
        del o
    else:
        o.refcount -= 1

def incrRefCount(o: redisObject) -> None:
    o.refcount += 1


def decrRefCountVoid(o: redisObject) -> None:
    decrRefCount(o)

REDIS_COMPARE_BINARY = (1<<0)
REDIS_COMPARE_COLL = (1<<1)

def compareStringObjectsWithFlags(a: 'robj', b: 'robj', flags: int) -> int:
    assert a.type == REDIS_STRING and b.type == REDIS_STRING

    bufa = bytearray(128)
    bufb = bytearray(128)

    if a is b:
        return 0

    if sdsEncodedObject(a):
        astr = a.ptr
        alen = sdslen(astr)
    else:
        alen = ll2string(bufa, len(bufa), ptr2long(a.ptr))
        astr = bufa

    if sdsEncodedObject(b):
        bstr = b.ptr
        blen = sdslen(bstr)
    else:
        blen = ll2string(bufb, len(bufb), ptr2long(b.ptr))
        bstr = bufb

    if flags & REDIS_COMPARE_COLL:
        return strcoll(astr, bstr)
    else:
        minlen = min(alen, blen)
        cmp = memcmp(astr, bstr, minlen)
        if cmp == 0:
            return alen - blen
        return cmp

def compareStringObjects(a: robj, b: robj) -> int:
    return compareStringObjectsWithFlags(a, b, REDIS_COMPARE_BINARY)

def equalStringObjects(a: robj, b: robj) -> bool:
    if (a.encoding == REDIS_ENCODING_INT and
        b.encoding == REDIS_ENCODING_INT):
        return a.ptr == b.ptr
    else:
        return compareStringObjects(a, b) == 0

def sdsEncodedObject(obj: robj) -> int:
    return (obj.encoding == REDIS_ENCODING_RAW or \
        obj.encoding == REDIS_ENCODING_EMBSTR)

def dictRedisObjectDestructor(privdata, val: Opt[redisObject]):
    if not val:
        return
    decrRefCount(val)
