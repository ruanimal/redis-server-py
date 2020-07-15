import socket
import errno
import typing
from logging import getLogger

from .ae import aeDeleteFileEvent, aeEventLoop, aeCreateFileEvent, AE_WRITABLE, AE_ERR
from .anet import anetTcpAccept
from .robject import (
    redisObject, incrRefCount, equalStringObjects, createObject, createStringObject,
    decrRefCount, dupStringObject, sdsEncodedObject, getDecodedObject,
    REDIS_STRING, REDIS_ENCODING_RAW, REDIS_ENCODING_EMBSTR, REDIS_ENCODING_INT
)
from .util import *
from .config import *
from .sds import (
    sdsempty, sdslen, sdsMakeRoomFor, sdsIncrLen, sdsrange, sdsnewlen, sdssplitargs, sds,
    sdscatlen, sdsfree
)
from .csix import cstr, ULONG_MASK
from .adlist import listDelNode, listFirst, listLength, listAddNodeTail, listNodeValue, listLast, rList, listNode

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


def freeClientAsync(c: 'RedisClient') -> None:
    if c.flags & REDIS_CLOSE_ASAP:
        return
    c.flags |= REDIS_CLOSE_ASAP
    server = get_server()
    server.clients_to_close.append(c)

def checkClientOutputBufferLimits(c: 'RedisClient') -> int:
    # TODO(rlj): something to do.
    pass

def asyncCloseClientOnOutputBufferLimitReached(c: 'RedisClient') -> None:
    assert c.reply_bytes < ULONG_MASK - 1024 * 64
    if c.reply_bytes == 0 or c.flags & REDIS_CLOSE_ASAP:
        return
    if checkClientOutputBufferLimits(c):
        freeClientAsync(c)
        logger.warning("Client %s scheduled to be closed ASAP for overcoming of output buffer limits.", c)

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


def dupLastObjectIfNeeded(reply: rList):
    assert listLength(reply) > 0
    ln = listLast(reply)
    cur = listNodeValue(ln)   # type: ignore
    if cur.refcount > 1:
        new = dupStringObject(cur)
        decrRefCount(cur)
        ln.value = new   # type: ignore
    return listNodeValue(ln)   # type: ignore

def getStringObjectSdsUsedMemory(o: redisObject) -> int:
    # NOTE: redis 应该是为了统计使用内存的大小, Python简单处理
    assert o.type == REDIS_STRING and isinstance(o.ptr, sds)
    return len(o.ptr.buf)

def _addReplySdsToList(c: 'RedisClient', s: sds) -> None:
    if c.flags & REDIS_CLOSE_AFTER_REPLY:
        sdsfree(s)
        return

    if listLength(c.reply) == 0:
        listAddNodeTail(c.reply, createObject(REDIS_STRING, s))
        c.reply_bytes += len(s.buf)
    else:
        tail: redisObject = listNodeValue(listLast(c.reply))   # type: ignore
        if (tail.ptr != None and tail.encoding == REDIS_ENCODING_RAW and
            sdslen(tail.ptr) + sdslen(s) <= REDIS_REPLY_CHUNK_BYTES):
            tail.ptr = dupLastObjectIfNeeded(c.reply).ptr
            sdscatlen(tail.ptr, s, sdslen(s))
        else:
            listAddNodeTail(c.reply, createObject(REDIS_STRING, s))
            c.reply_bytes += len(s.buf)
    asyncCloseClientOnOutputBufferLimitReached(c)


def _addReplyStringToList(c: 'RedisClient', s: cstr, length: int) -> None:
    if c.flags & REDIS_CLOSE_AFTER_REPLY:
        return
    if listLength(c.reply) == 0:
        o = createStringObject(s, length)
        listAddNodeTail(c.reply, o)
        c.reply_bytes += getStringObjectSdsUsedMemory(o)
    else:
        tail: redisObject = listNodeValue(listLast(c.reply))   # type: ignore
        if (tail.ptr != None and tail.encoding == REDIS_ENCODING_RAW and
            sdslen(tail.ptr) + length <= REDIS_REPLY_CHUNK_BYTES):
            tail.ptr = dupLastObjectIfNeeded(c.reply).ptr
            sdscatlen(tail.ptr, s, length)
        else:
            o = createStringObject(s, length)
            listAddNodeTail(c.reply, o)
            c.reply_bytes += getStringObjectSdsUsedMemory(o)
    asyncCloseClientOnOutputBufferLimitReached(c)


def _addReplyObjectToList(c: 'RedisClient', o: redisObject) -> None:
    if c.flags & REDIS_CLOSE_AFTER_REPLY:
        return
    if listLength(c.reply) == 0:
        incrRefCount(o)
        listAddNodeTail(c.reply, o)
        c.reply_bytes += getStringObjectSdsUsedMemory(o)
    else:
        tail = listNodeValue(listLast(c.reply))   # type: ignore
        if (tail.ptr != None and tail.encoding == REDIS_ENCODING_RAW and
            sdslen(tail.ptr) + sdslen(o.ptr) <= REDIS_REPLY_CHUNK_BYTES):
            c.reply_bytes -= sdslen(tail.ptr)
            tail.ptr = dupLastObjectIfNeeded(c.reply).ptr
            sdscatlen(tail.ptr, o.ptr, sdslen(o.ptr))
            c.reply_bytes += sdslen(tail.ptr)
        else:
            incrRefCount(o)
            listAddNodeTail(c.reply, o)
            c.reply_bytes += getStringObjectSdsUsedMemory(o)
    asyncCloseClientOnOutputBufferLimitReached(c)

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
    if prepareClientToWrite(c) != REDIS_OK:
        return
    if sdsEncodedObject(obj):
        if _addReplyToBuffer(c, obj.ptr, sdslen(obj.ptr)) != REDIS_OK:
            _addReplyObjectToList(c, obj)
    elif obj.encoding == REDIS_ENCODING_INT:
        if listLength(c.reply) == 0 and (len(c.buf) - c.bufpos) >= 32:
            buf = bytearray(32)
            length = ll2string(buf, len(buf), obj.ptr)
            if _addReplyToBuffer(c, buf, length) == REDIS_OK:
                return
        obj = getDecodedObject(obj)
        if _addReplyToBuffer(c, obj.ptr, sdslen(obj.ptr)) != REDIS_OK:
            _addReplyObjectToList(c, obj)
        decrRefCount(obj)
    else:
        raise ValueError("Wrong obj->encoding in addReply(): %r", obj)

def addReplyLongLongWithPrefix(c: 'RedisClient', ll: int, prefix: str) -> None:
    buf = bytearray(128)
    shared = get_shared()
    if prefix == '*' and ll < ServerConfig.REDIS_SHARED_BULKHDR_LEN:
        addReply(c, shared.mbulkhdr[ll])
        return
    elif prefix == '$' and ll < ServerConfig.REDIS_SHARED_BULKHDR_LEN:
        addReply(c, shared.bulkhdr[ll])
        return
    buf[0:1] = prefix.encode()
    tmp = memoryview(buf)[1:]
    length = ll2string(tmp, len(buf)-1, ll)
    buf[length+1] = ord('\r')
    buf[length+2] = ord('\n')
    addReplyString(c, buf, length+3)

def addReplyBulkLen(c: 'RedisClient', obj: redisObject) -> None:
    if sdsEncodedObject(obj):
        length = sdslen(obj.ptr)
    else:
        length = len(str(obj.ptr))
    if length < ServerConfig.REDIS_SHARED_BULKHDR_LEN:
        addReply(c, get_shared().bulkhdr[length])
    else:
        addReplyLongLongWithPrefix(c, length, '$')

def addReplyBulk(c: 'RedisClient', obj: redisObject) -> None:
    shared = get_shared()
    addReplyBulkLen(c, obj)
    addReply(c, obj)
    addReply(c, shared.crlf)

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
    ll = 0
    pos = 0
    if c.multibulklen == 0:
        assert c.argc == 0
        assert c.querybuf[0:1] == b'*'
        newline = c.querybuf[0:c.querybuf.buf.find(b'\r\n')]
        if not newline:
            if sdslen(c.querybuf) > REDIS_INLINE_MAX_SIZE:
                addReplyError(c, "Protocol error: too big mbulk count string")
                setProtocolError(c, 0)
            return REDIS_ERR
        ok, ll = string2ll(newline[1:], len(newline)-1)
        if not ok or ll > 1024 * 1024:
            addReplyError(c, "Protocol error: invalid multibulk length")
            setProtocolError(c, 0)
        pos = len(newline) + 2
        if ll <= 0:
            sdsrange(c.querybuf, pos, -1)
            return REDIS_OK
        c.multibulklen = ll
    assert c.multibulklen > 0
    while c.multibulklen:
        if c.bulklen == -1:
            newpos = c.querybuf.buf.find(b'\r\n', pos)
            if newpos < 0:
                if sdslen(c.querybuf) > REDIS_INLINE_MAX_SIZE:
                    addReplyError(c, "Protocol error: too big bulk count string")
                    setProtocolError(c, 0)
                    return REDIS_ERR
                break
            if c.querybuf[pos:pos+1] != b'$':
                addReplyError(c, "Protocol error: expected '$', got %r" % c.querybuf[pos:pos+1])
                setProtocolError(c, pos)
                return REDIS_ERR
            ok, ll = string2ll(c.querybuf[pos+1:newpos], newpos-(pos+1))
            if not ok or ll < 0 or ll > 512*1024*1024:
                addReplyError(c, "Protocol error: invalid bulk length")
                setProtocolError(c, pos)
                return REDIS_ERR
            pos = newpos + 2
            if ll >= REDIS_MBULK_BIG_ARG:
                sdsrange(c.querybuf, pos, -1)
                pos = 0
                qblen = sdslen(c.querybuf)
                if qblen < ll + 2:
                    c.querybuf = sdsMakeRoomFor(c.querybuf, ll+2-qblen)
            c.bulklen = ll
        if sdslen(c.querybuf)-pos < c.bulklen + 2:
            break
        else:
            if pos == 0 and c.bulklen >= REDIS_MBULK_BIG_ARG and sdslen(c.querybuf) == c.bulklen+2:
                c.argv.append(createObject(REDIS_STRING, c.querybuf))
                sdsIncrLen(c.querybuf, -2)
                c.querybuf = sdsempty()
                c.querybuf = sdsMakeRoomFor(c.querybuf, c.bulklen+2)
                pos = 0
            else:
                c.argv.append(createStringObject(c.querybuf[pos:pos+c.bulklen], c.bulklen))
                pos += c.bulklen+2
            c.bulklen = -1
            c.multibulklen -= 1

    if pos:
        sdsrange(c.querybuf, pos, -1)
    if c.multibulklen == 0:
        return REDIS_OK
    return REDIS_ERR

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
            if c.querybuf[0:1] == b'*':
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
    chunk = sock.recv(readlen)
    nread = len(chunk)
    if nread:
        c.querybuf[qlen:qlen+nread] = chunk
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

def sendReplyToClient(ae: aeEventLoop, fd: int, privdata: 'RedisClient', mask: int):
    from .redis import freeClient
    c = privdata
    totwritten = 0
    sock = SocketCache.get(fd)
    server = get_server()
    err = None
    while c.bufpos > 0 or listLength(c.reply):
        if c.bufpos > 0:
            try:
                sock.sendall(memoryview(c.buf)[:c.bufpos])
            except OSError as e:
                err = e
                break
            totwritten += len(c.buf)
            c.sentlen += len(c.buf)
            c.bufpos = 0
            c.sentlen = 0
        else:
            o = listNodeValue(listFirst(c.reply))  # type: ignore
            objlen = sdslen(o.ptr)
            objmem = getStringObjectSdsUsedMemory(o)
            if objlen == 0:
                listDelNode(c.reply, listFirst(c.reply))  # type: ignore
                c.reply_bytes -= objmem
                continue
            try:
                sock.sendall(o.ptr.content)
            except OSError as e:
                err = e
                break
            totwritten += objlen
            c.sentlen += objlen
            if c.sentlen == objlen:
                listDelNode(c.reply, listFirst(c.reply))  # type: ignore
                c.sentlen = 0
                c.reply_bytes -= objmem
        if (totwritten > ServerConfig.REDIS_MAX_WRITE_PER_EVENT and
            (server.maxmemory == 0 or zmalloc_used_memory() < server.maxmemory)):
            break
    if err and err.errno != errno.EAGAIN:
        logger.info("Error writing to client: %s", err)
        freeClient(c)
    if totwritten > 0 and not (c.flags & REDIS_MASTER):
        c.lastinteraction = server.unixtime
    if c.bufpos == 0 and listLength(c.reply) == 0:
        c.sentlen = 0
        aeDeleteFileEvent(server.el, c.fd.fileno(), AE_WRITABLE)   # type: ignore
        if c.flags & REDIS_CLOSE_AFTER_REPLY:
            freeClient(c)


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
