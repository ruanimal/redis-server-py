import typing

if typing.TYPE_CHECKING:
    from ..redis import RedisClient

from ..db import lookupKeyReadOrReply
from ..util import get_shared
from ..config import *
from ..robject import REDIS_STRING
from ..networking import addReply, addReplyBulk

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

def setCommand(c: 'RedisClient') -> int:
    pass
