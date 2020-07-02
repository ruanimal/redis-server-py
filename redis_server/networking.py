import socket
import errno
import typing
from logging import getLogger
from .ae import aeEventLoop, aeCreateFileEvent, AE_WRITABLE, AE_ERR
from .anet import anetTcpAccept
from .robject import (
    redisObject, incrRefCount, equalStringObjects, createObject, compareStringObjects,
    REDIS_STRING, REDIS_ENCODING_RAW, REDIS_ENCODING_EMBSTR,
)
from .util import SocketCache, get_server
from .config import *
from .sds import sdslen, sdsMakeRoomFor, sdsIncrLen, sdsrange, sdsnewlen, sdssplitargs, sds
from .csix import cstr
from .adlist import listLength, listAddNodeTail

if typing.TYPE_CHECKING:
    from .redis import RedisClient

logger = getLogger(__name__)

MAX_ACCEPTS_PER_CALL = 1000

def askingCommand():
    # NOTE: for cluster uasge
    pass

def clientsArePaused() -> int:
    server = get_server()
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
    server = get_server()
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
    server = get_server()
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
    from .redis import freeClient
    server = get_server()
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

def sendReplyToClient():
    # TODO(rlj): something to do.
    pass

def prepareClientToWrite(c: 'RedisClient') -> int:
    server = get_server()
    if c.flags & REDIS_LUA_CLIENT:
        return REDIS_OK
    if (c.flags & REDIS_MASTER) and not(c.flags & REDIS_MASTER_FORCE_REPLY):
        return REDIS_ERR
    if not c.fd or c.fd.fileno() <= 0:
        return REDIS_ERR
    if (c.bufpos == 0 and listLength(c.reply) == 0
        and (c.replstate in (REDIS_REPL_NONE, REDIS_REPL_ONLINE))
        and aeCreateFileEvent(server.el, c.fd.fileno(), AE_WRITABLE, sendReplyToClient, c) == AE_ERR
        ):
        return REDIS_ERR
    return REDIS_OK


def _addReplyToBuffer(c: 'RedisClient', s: cstr, length: int) -> int:
    available = len(c.buf) - c.bufpos
    if c.flags & REDIS_CLOSE_AFTER_REPLY:
        return REDIS_OK
    if listLength(c.reply) > 0:
        return REDIS_ERR
    if length > available:
        return REDIS_ERR
    c.buf[c.bufpos:c.bufpos+length] = s[:length]
    c.bufpos += length
    return REDIS_OK


def getStringObjectSdsUsedMemory(o: redisObject) -> int:
    # NOTE: redis 应该是为了统计使用内存的大小, Python简单处理
    assert o.type == REDIS_STRING and isinstance(o.ptr, sds)
    return len(o.ptr.buf)

def _addReplyStringToList(c: 'RedisClient', s: cstr, length: int) -> int:
    if c.flags & REDIS_CLOSE_AFTER_REPLY:
        return
    if listLength(c.reply) == 0:
        o = compareStringObjects(s, length)
        incrRefCount(o)
        listAddNodeTail(c.reply, o)
        c.reply_bytes += getStringObjectSdsUsedMemory(o)
        # TODO(rlj): something to do.

def addReplyString(c: 'RedisClient', s: cstr, length: int) -> None:
    if prepareClientToWrite(c) != REDIS_OK:
        return
    if _addReplyToBuffer(c, s, length) != REDIS_OK:
        _addReplyStringToList(c, s, length)


def addReplyErrorLength(c: 'RedisClient', s: cstr, length: int) -> None:
    addReplyString(c, b"-ERR ", 5)
    addReplyString(c, s, length)
    addReplyString(c, b"\r\n", 2)

def addReplyError(c: 'RedisClient', err: str) -> None:
    msg = err.encode()
    addReplyErrorLength(c, msg, len(msg))

def addReply(c: 'RedisClient', obj: redisObject) -> None:
    pass
