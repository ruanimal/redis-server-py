import socket
import errno
import typing
from logging import getLogger
from .ae import aeEventLoop
from .anet import anetTcpAccept
from .robject import redisObject, incrRefCount, equalStringObjects, createObject, REDIS_STRING
from .util import SocketCache
from .config import *
from .sds import sdslen, sdsMakeRoomFor, sdsIncrLen, sdsrange, sdsnewlen, sdssplitargs

if typing.TYPE_CHECKING:
    from .redis import RedisClient

logger = getLogger(__name__)

MAX_ACCEPTS_PER_CALL = 1000

def askingCommand():
    # NOTE: for cluster uasge
    pass

def clientsArePaused() -> int:
    from .redis import RedisServer
    server = RedisServer()
    if server.clients_paused and server.clients_pause_end_time < server.unixtime:
        server.clients_paused = 0
        for c in server.clients:
            if c.flags & REDIS_SLAVE:
                continue
            server.unblocked_clients.append(c)
    return server.clients_paused

def freeClientArgv(c: 'RedisClient') -> None:
    from .robject import decrRefCount
    for i in c.argv:
        decrRefCount(i)
    c.argv = []
    c.cmd = None

def setProtocolError(c: 'RedisClient', pos: int) -> None:
    from .redis import RedisServer
    server = RedisServer()
    if server.verbosity >= REDIS_VERBOSE:
        logger.info("Protocol error from client: %s", c)
    c.flags |= REDIS_CLOSE_AFTER_REPLY
    sdsrange(c.querybuf, pos, -1)


def resetClient(c: 'RedisClient') -> None:
    prevcmd = c.cmd and c.cmd.proc or None
    freeClientArgv(c)
    c.reqtype = 0
    c.multibulklen = 0
    c.bulklen = -1
    if (not (c.flags & REDIS_MULTI) and prevcmd != askingCommand):
        c.flags &= (~REDIS_ASKING)

def processInlineBuffer(c: 'RedisClient') -> int:
    from .redis import RedisServer
    server = RedisServer()
    idx = c.querybuf.buf.find(b'\n')
    if idx == -1 or idx == 0:   # buffer 不包含换行
        if sdslen(c.querybuf) > REDIS_INLINE_MAX_SIZE:
            addReplyError(c, "Protocol error: too big inline request")
            setProtocolError(c, 0)
        return REDIS_ERR
    newline = memoryview(c.querybuf.buf)[:idx]
    if newline[-1] == b'\r':
        newline = newline[:-1]
    querylen = len(newline)
    aux = sdsnewlen(c.querybuf.buf, querylen)
    argv = sdssplitargs(aux)
    if not argv:
        addReplyError(c, "Protocol error: unbalanced quotes in request")
        setProtocolError(c, 0)
        return REDIS_ERR
    if querylen == 0 and c.flags & REDIS_SLAVE:
        c.repl_ack_time = server.unixtime
    sdsrange(c.querybuf, querylen+2, -1)
    c.argv = [createObject(REDIS_STRING, i) for i in argv]
    return REDIS_OK

def processMultibulkBuffer(c: 'RedisClient'):
    pass


def processInputBuffer(c: 'RedisClient') -> None:
    from .redis import processCommand
    while sdslen(c.querybuf) > 0:
        if (not (c.flags & REDIS_SLAVE) and clientsArePaused()):
            return
        if c.flags & REDIS_BLOCKED:
            return
        if c.flags & REDIS_CLOSE_AFTER_REPLY:
            return
        if not c.reqtype:
            if c.querybuf[0] == '*':
                c.reqtype = REDIS_REQ_MULTIBULK
            else:
                c.reqtype = REDIS_REQ_INLINE
        if c.reqtype == REDIS_REQ_INLINE:
            if (processInlineBuffer(c) != REDIS_OK):
                break
        elif c.reqtype == REDIS_REQ_MULTIBULK:
            if (processMultibulkBuffer(c) != REDIS_OK):
                break
        else:
            raise ValueError("Unknown request type: %r", c.reqtype)
        if c.argc == 0:
            resetClient(c)
        else:
            if processCommand(c) == REDIS_OK:
                resetClient(c)


def readQueryFromClient(el: aeEventLoop, fd: int, privdata: 'RedisClient', mask: int) -> None:
    from .redis import RedisServer, freeClient
    server = RedisServer()
    c = server.current_client = privdata

    readlen = REDIS_IOBUF_LEN
    if (c.reqtype == REDIS_REQ_MULTIBULK and c.multibulklen != -1
        and c.bulklen >= REDIS_MBULK_BIG_ARG):
        remaining = c.bulklen+2 - sdslen(c.querybuf)
        if remaining < readlen:
            readlen = remaining

    qlen = sdslen(c.querybuf)
    if c.querybuf_peak < qlen:
        c.querybuf_peak = qlen
    c.querybuf = sdsMakeRoomFor(c.querybuf, readlen)
    sock = SocketCache.get(fd)
    nread = sock.recv_into(memoryview(c.querybuf.buf)[qlen:], readlen)
    if nread:
        sdsIncrLen(c.querybuf, nread)
        c.lastinteraction = server.unixtime
    else:
        server.current_client = None
        return
    if sdslen(c.querybuf) > server.client_max_querybuf_len:
        logger.warning('Closing client that reached max query buffer length: %s', c)
        freeClient(c)
    processInputBuffer(c)
    server.current_client = None

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
    # fd.sendall(b'Hello world!\r\n')   # NOTE: test

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

def addReplyError(c: 'RedisClient', err: str) -> None:
    pass
