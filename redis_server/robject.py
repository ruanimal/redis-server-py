import typing
from typing import List, Callable, Optional as Opt, Tuple, Union, ByteString
from .sds import sdslen, sdsnewlen, sds, sdsfree, sdsavail, sdsRemoveFreeSpace, sdsnew
from .util import ll2string, string2l, get_shared, get_server
from .csix import ptr2long, strcoll, memcmp, cstr, int2cstr
from .config import *

if typing.TYPE_CHECKING:
    from .redis import RedisClient

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

    @property
    def int_value(self) -> int:
        assert self.encoding == REDIS_ENCODING_INT
        return self.ptr

robj = redisObject


def createObject(obj_type: int, ptr, encoding: int = REDIS_ENCODING_RAW) -> robj:
    from .redis import LRUClock
    o = redisObject()
    o.type = obj_type
    o.encoding = encoding
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
def createStringObject(ptr: Union[cstr, str], length: int) -> robj:
    if isinstance(ptr, str):
        ptr = ptr.encode('utf8')
    if (length <= REDIS_ENCODING_EMBSTR_SIZE_LIMIT):
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
        cmp = memcmp(astr.content, bstr.content, minlen)
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

def dupStringObject(o: robj) -> robj:
    assert o.type == REDIS_STRING
    if o.encoding == REDIS_ENCODING_RAW:
        return createRawStringObject(o.ptr, sdslen(o.ptr))
    elif o.encoding == REDIS_ENCODING_EMBSTR:
        return createEmbeddedStringObject(o.ptr, sdslen(o.ptr))
    elif o.encoding == REDIS_ENCODING_INT:
        d = createObject(REDIS_STRING, None)
        d.encoding = REDIS_ENCODING_INT
        d.ptr = o.ptr
        return d
    else:
        raise ValueError("Wrong encoding: %r", o.encoding)

def getDecodedObject(o: robj) -> robj:
    if sdsEncodedObject(o):
        incrRefCount(o)
        return o
    if o.type == REDIS_STRING and o.encoding == REDIS_ENCODING_INT:
        buf = bytearray(32)
        ll2string(buf, 32, o.ptr)
        dec = createStringObject(buf, len(buf))
        return dec
    else:
        raise ValueError("Unknown encoding type")

def tryObjectEncoding(o: robj) -> robj:
    assert o.type == REDIS_STRING
    s = o.ptr
    if not sdsEncodedObject(o):
        return o
    if o.refcount > 1:
        return o
    shared = get_shared()
    server = get_server()
    length = sdslen(s)
    flag, value = string2l(s, length)
    # 只对长度小于或等于 21 字节，并且可以被解释为整数的字符串进行编码, 编码为整数
    if length < 21 and flag:
        if server.maxmemory == 0 and value >= 0 and value < ServerConfig.REDIS_SHARED_INTEGERS:
            decrRefCount(o)
            incrRefCount(shared.integers[value])
            return shared.integers[value]
        else:
            if o.encoding == REDIS_ENCODING_RAW:
                sdsfree(o.ptr)
            o.encoding = REDIS_ENCODING_INT
            o.ptr = value
            return o
    # 尝试将 RAW 编码的字符串编码为 EMBSTR 编码
    if length <= REDIS_ENCODING_EMBSTR_SIZE_LIMIT:
        if o.encoding == REDIS_ENCODING_EMBSTR:
            return o
        emb = createEmbeddedStringObject(s, sdslen(s))
        decrRefCount(o)
        return emb
    if o.encoding == REDIS_ENCODING_RAW and sdsavail(s) > length // 10:
        o.ptr = sdsRemoveFreeSpace(o.ptr)
    return o

def getLongLongFromObject(o: robj) -> Tuple[int, int]:
    value = 0
    if o == None:
        value = 0
    else:
        assert o.type == REDIS_STRING
        if sdsEncodedObject(o):
            try:
                value = int(o.ptr.content, 10)
            except ValueError:
                return REDIS_ERR, value
        elif o.encoding == REDIS_ENCODING_INT:
            value = o.ptr
        else:
            raise RuntimeError("Unknown string encoding")
    return REDIS_OK, value

def getLongLongFromObjectOrReply(c: 'RedisClient', o: robj, msg: Opt[str]) -> Tuple[int, int]:
    from .networking import addReplyError
    status, value = getLongLongFromObject(o)
    if status != REDIS_OK:
        if msg:
            addReplyError(c, msg)
        else:
            addReplyError(c, "value is not an integer or out of range")
        return REDIS_ERR, 0
    return REDIS_OK, value
