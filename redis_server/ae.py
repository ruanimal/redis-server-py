from typing import List, Callable, Optional as Opt, Tuple
import time
from datetime import datetime, timedelta
from collections import namedtuple
from .csix import cstr

# 事件执行状态
## 成功
AE_OK = 0
## 出错
AE_ERR = -1

# 文件事件状态
## 未设置
AE_NONE = 0
## 可读
AE_READABLE = 1
## 可写
AE_WRITABLE = 2

# 时间处理器的执行 flags
## 文件事件
AE_FILE_EVENTS = 1
## 时间事件
AE_TIME_EVENTS = 2
## 所有事件
AE_ALL_EVENTS = (AE_FILE_EVENTS|AE_TIME_EVENTS)
## 不阻塞，也不进行等待
AE_DONT_WAIT = 4

# 决定时间事件是否要持续执行的 flag
AE_NOMORE = -1

class aeFileEvent:
    def __init__(self):
        self.mask: int = 0
        self.rfileProc = None
        self.wfileProc = None
        self.clientData = None

class aeTimeEvent:
    def __init__(self):
        self.id: int = 0
        self.when_sec: int = None
        self.when_ms: int = None
        self.timeProc = None
        self.finalizerProc = None
        self.clientData = None
        self.next: 'aeTimeEvent' = None

class aeFiredEvent:
    def __init__(self):
        self.fd: int = 0
        self.mask: int = 0

class aeEventLoop:
    def __init__(self):
        self.maxfd: int = 0
        self.setsize: int = 0
        self.timeEventNextId: int = 0
        self.setsize: int = 0
        self.lastTime: datetime = None
        self.events: List[aeFileEvent] = None
        self.fired: List[aeFiredEvent] = None
        self.timeEventHead: aeTimeEvent = None
        self.stop: int = 0
        self.apidata = None
        self.beforesleep: Opt[Callable[[aeEventLoop], None]] = None

def aeCreateEventLoop(setsize: int) -> aeEventLoop:
    eventLoop = aeEventLoop()
    eventLoop.events = [aeFileEvent for _ in range(setsize)]
    eventLoop.fired = [aeFiredEvent for _ in range(setsize)]
    eventLoop.setsize = setsize
    eventLoop.lastTime = datetime.now()
    eventLoop.timeEventHead = None
    eventLoop.timeEventNextId = 0
    eventLoop.stop = 0
    eventLoop.maxfd = -1
    eventLoop.beforesleep = None
    aeApiCreate(eventLoop)
    for i in range(setsize):
        eventLoop.events[i].mask = AE_NONE
    return eventLoop

def aeDeleteEventLoop(eventLoop: aeEventLoop) -> int:
    aeApiFree(eventLoop)

def aeStop(eventLoop: aeEventLoop) -> None:
    eventLoop.stop = 1

def aeCreateFileEvent(eventLoop: aeEventLoop, fd: int,
                      mask: int, proc: Callable, clientData: cstr) -> None:
    if fd >= eventLoop.setsize:
        raise RuntimeError(AE_ERR)

    fe = eventLoop.events[fd]
    if aeApiAddEvent(eventLoop, fd, mask) == -1:
        return AE_ERR

    fe.mask |= mask
    if mask & AE_READABLE:
        fe.rfileProc = proc
    if mask & AE_WRITABLE:
        fe.wfileProc = proc
    fe.clientData = clientData
    if fd > eventLoop.maxfd:
        eventLoop.maxfd = fd
    return AE_OK

def aeDeleteFileEvent(eventLoop: aeEventLoop, fd: int, mask: int) -> None:
    if fd >= eventLoop.setsize:
        return
    if eventLoop.events[fd].mask == AE_NONE:
        return

    fe = eventLoop.events[fd]
    fe.mask = fe.mask & (~mask)
    if fd == eventLoop.maxfd and fe.mask == AE_NONE:
        j = eventLoop.maxfd-1
        for j in range(eventLoop.maxfd-1, -1, -1):
            if eventLoop.events[j].mask != AE_NONE:
                break
        eventLoop.maxfd = j
    aeApiDelEvent(eventLoop, fd, mask)

def aeGetFileEvents(eventLoop: aeEventLoop, fd: int) -> int:
    if fd >= eventLoop.setsize:
        return 0
    return eventLoop.events[fd].mask

def aeCreateTimeEvent(eventLoop: aeEventLoop, milliseconds: int,
                      proc: Callable, clientData: cstr, finalizerProc: Callable) -> None:
    ident = eventLoop.timeEventNextId + 1
    te = aeTimeEvent()
    te.id = ident
    te.when_sec, te.when_ms = aeAddMillisecondsToNow(milliseconds)
    te.timeProc = proc
    te.finalizerProc = finalizerProc
    te.clientData = clientData
    te.next = eventLoop.timeEventHead
    eventLoop.timeEventHead = te
    return ident

def aeDeleteTimeEvent(eventLoop: aeEventLoop, ident: int):
    te = eventLoop.timeEventHead
    prev = None
    while te:
        if te.id == ident:
            if prev == None:
                eventLoop.timeEventHead = te.next
            else:
                prev.next = te.next
            if te.finalizerProc:
                te.finalizerProc(eventLoop, te.clientData)
            return AE_OK
        prev = te
        te = te.next
    return AE_ERR

def processTimeEvents(eventLoop: aeEventLoop) -> int:
    processed = 0
    now = datetime.now()

    # 防止系统时间修改导致事件混乱
    if now < eventLoop.lastTime:
        te = eventLoop.timeEventHead
        while te:
            te.when_sec = 0
            te = te.next
    eventLoop.lastTime = now

    te = eventLoop.timeEventHead
    maxId = eventLoop.timeEventNextId - 1
    while te:
        if te.id > maxId:
            te = te.next
            continue
        now_sec, now_ms = aeGetTime()
        if now_sec > te.when_sec or (now_sec == te.when_ms and now_ms >= te.when_ms):
            ident = te.id
            retval = te.timeProc(eventLoop, ident, te.clientData)
            processed += 1
            if retval != AE_NOMORE:
                te.when_sec, te.when_ms = aeAddMillisecondsToNow(retval)
            else:
                aeDeleteTimeEvent(eventLoop, ident)
            te = eventLoop.timeEventHead
        else:
            te = te.next
    return processed


def aeProcessEvents(eventLoop: aeEventLoop, flags: int):
    processed = 0
    numevents = 0

    if (not (flags & AE_TIME_EVENTS)) and (not (flags & AE_FILE_EVENTS)):
        return 0

    tv = None
    if eventLoop.maxfd != -1 or ((flags & AE_TIME_EVENTS) and not(flags & AE_DONT_WAIT)):
        shortest = None
        if (flags & AE_TIME_EVENTS) and not(flags & AE_DONT_WAIT):
            shortest = aeSearchNearestTimer(eventLoop)
        if shortest:
            now_sec, now_ms = aeGetTime()
            tv = timeval()
            tv.tv_sec = shortest.when_sec - now_sec
            if shortest.when_ms < now_ms:
                tv.tv_usec = (shortest.when_ms + 1000 - now_ms) * 1000
                tv.tv_sec -= 1
            else:
                tv.tv_usec = (shortest.when_ms - now_ms) * 1000
            if tv.tv_sec < 0:
                tv.tv_sec = 0
            if tv.tv_usec < 0:
                tv.tv_usec = 0
        else:
            if flags & AE_DONT_WAIT:
                tv.tv_sec = tv.tv_usec = 0
            else:
                tv = None
    numevents = aeApiPoll(eventLoop, tv)
    for j in range(numevents):
        fe = eventLoop.events[eventLoop.fired[j].fd]
        mask = eventLoop.fired[j].mask
        fd = eventLoop.fired[j].fd
        rfired = 0
        if fe.mask & mask & AE_READABLE:
            rfired = 1
            fe.rfileProc(eventLoop, fd, fe.clientData, mask)
        if fe.mask & mask & AE_WRITABLE:
            if not rfired or (fe.wfileProc != fe.rfileProc):
                fe.wfileProc(eventLoop, fd, fe.clientData, mask)
        processed += 1
    if flags & AE_TIME_EVENTS:
        processed += processTimeEvents(eventLoop)
    return processed


# int aeWait(int fd, int mask, long long milliseconds);
# void aeMain(aeEventLoop *eventLoop);
# char *aeGetApiName(void);
# void aeSetBeforeSleepProc(aeEventLoop *eventLoop, aeBeforeSleepProc *beforesleep);
# int aeGetSetSize(aeEventLoop *eventLoop);
# int aeResizeSetSize(aeEventLoop *eventLoop, int setsize);

### private functions ###

def aeAddMillisecondsToNow(milliseconds):
    cur_sec, cur_ms = aeGetTime()
    when_sec = cur_sec + milliseconds // 1000
    when_ms = cur_ms + milliseconds % 1000
    if when_ms >= 1000:
        when_sec += 1
        when_ms -= 1000
    return when_sec, when_ms

def aeGetTime() -> Tuple[int, int]:
    now = datetime.now()
    return int(now.timestamp()), now.microsecond // 1000

def aeSearchNearestTimer(eventLoop: aeEventLoop) -> aeTimeEvent:
    te = eventLoop.timeEventHead
    nearest = None
    while te:
        if not nearest or (te.when_sec < nearest.when_sec or
            (te.when_sec == nearest.when_sec and te.when_ms < nearest.when_ms)):
            nearest = te
        te = te.next
    return nearest

class timeval:
    def __init__(self):
        self.tv_sec: int = 0
        self.tv_usec: int = 0

### end private functions ###


def aeApiCreate(eventLoop: aeEventLoop) -> int:
    pass

def aeApiFree(eventLoop: aeEventLoop) -> int:
    pass

def aeApiAddEvent(eventLoop: aeEventLoop, fd: int, mask: int) -> int:
    pass

def aeApiDelEvent(eventLoop: aeEventLoop, fd: int, mask: int) -> int:
    pass

def aeApiPoll(eventLoop: aeEventLoop, tvp: timeval) -> int:
    pass
