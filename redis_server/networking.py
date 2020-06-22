import socket
import errno
from logging import getLogger
from .ae import aeEventLoop
from .anet import anetTcpAccept
from .robject import redisObject, incrRefCount, equalStringObjects
from .util import SocketCache

logger = getLogger(__name__)

MAX_ACCEPTS_PER_CALL = 1000

def readQueryFromClient():
    pass

def dupClientReplyValue(o: redisObject) -> redisObject:
    incrRefCount(o)
    return o

def listMatchObjects(a: redisObject, b: redisObject):
    return equalStringObjects(a, b)

def acceptCommonHandler(fd: socket.socket, flags: int) -> None:
    from .redis import createClient, freeClient, RedisServer

    server = RedisServer()
    c = createClient(server, fd)
    if not c:
        fd.close()
        return

    if len(server.clients) > server.maxclients:
        err = b"-ERR max number of clients reached\r\n"
        fd.sendall(err)
        server.stat_rejected_conn += 1
        freeClient(c)
        return
    server.stat_numcommands += 1
    c.flags |= flags
    fd.sendall(b'Hello world!\r\n')   # NOTE: test

def acceptTcpHandler(el: aeEventLoop, fd: int, privdata, mask: int):
    max_ = MAX_ACCEPTS_PER_CALL

    while max_:
        max_ -= 1
        sfd = SocketCache.get(fd)
        try:
            cfd, addr = anetTcpAccept(sfd)
        except OSError as e:
            if e.errno == errno.EWOULDBLOCK:
                logger.warning("Accepting client connection: %s", e)
            return
        logger.info('Accepted %s:%s', *addr)
        acceptCommonHandler(cfd, 0)

def acceptUnixHandler(*args):
    pass
