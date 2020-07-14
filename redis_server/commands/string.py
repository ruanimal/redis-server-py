import typing

if typing.TYPE_CHECKING:
    from ..redis import RedisClient
from typing import Optional as Opt
from ..db import lookupKeyReadOrReply, lookupKeyWrite, setKey, notifyKeyspaceEvent, setExpire
from ..util import get_shared, get_server
from ..config import *
from ..robject import *
from ..networking import addReply, addReplyBulk
from ..csix import timeval

__all__ = [
    'getGenericCommand',
    'getCommand',
    'setGenericCommand',
    'setCommand',
]

REDIS_SET_NO_FLAGS = 0
REDIS_SET_NX = (1<<0)   #  /* Set if key not exists. */
REDIS_SET_XX = (1<<1)   #  /* Set if key exists. */


def getGenericCommand(c: 'RedisClient') -> int:
    shared = get_shared()
    o = lookupKeyReadOrReply(c, c.argv[1], shared.nullbulk)
    if o == None:
        return REDIS_OK
    assert o
    if o.type != REDIS_STRING:
        addReply(c, shared.wrongtypeerr)
        return REDIS_ERR
    else:
        addReplyBulk(c, o)
        return REDIS_OK

def getCommand(c: 'RedisClient'):
    getGenericCommand(c)


def setGenericCommand(c: 'RedisClient', flags: int, key: robj, val: robj, expire: Opt[robj],
                      unit: int, ok_reply: Opt[robj], abort_reply: Opt[robj]):
    from ..networking import addReply, addReplyError
    milliseconds = 0
    if expire:
        status, milliseconds = getLongLongFromObjectOrReply(c, expire, '')
        if status != REDIS_OK:
            return
        if milliseconds <= 0:
            addReplyError(c, "invalid expire time in SETEX")
            return
        if unit == UNIT_SECONDS:
            milliseconds *= 1000
    shared = get_shared()
    if (((flags & REDIS_SET_NX) and lookupKeyWrite(c.db, key) != None) or
        ((flags & REDIS_SET_XX) and lookupKeyWrite(c.db, key) == None)):
        addReply(c, abort_reply and abort_reply or shared.nullbulk)
        return
    setKey(c.db, key, val)
    server = get_server()
    server.dirty += 1
    if expire:
        setExpire(c.db, key, timeval.from_datetime().mstime + milliseconds)
    notifyKeyspaceEvent(REDIS_NOTIFY_STRING, 'set', key, c.db.id)
    if expire:
        notifyKeyspaceEvent(REDIS_NOTIFY_GENERIC, 'set', key, c.db.id)
    addReply(c, ok_reply and ok_reply or shared.ok)


def setCommand(c: 'RedisClient'):
    unit = UNIT_SECONDS
    flags = REDIS_SET_NO_FLAGS
    expire = None
    j = 3
    shared = get_shared()
    while j < c.argc:
        a = c.argv[j].ptr
        ne = None if j == c.argc-1 else c.argv[j+1]
        if a.buf.lower() == b'nx\0':
            flags |= REDIS_SET_NX
        elif a.buf.lower() == b'xx\0':
            flags |= REDIS_SET_XX
        elif a.buf.lower() == b'ex\0':
            unit = UNIT_SECONDS
            expire = ne
            j += 1
        elif a.buf.lower() == b'px\0':
            unit = UNIT_MILLISECONDS
            expire = ne
            j += 1
        else:
            addReply(c, shared.syntaxerr)
            return
        j += 1
    c.argv[2] = tryObjectEncoding(c.argv[2])
    setGenericCommand(c, flags, c.argv[1], c.argv[2], expire, unit, None, None)
