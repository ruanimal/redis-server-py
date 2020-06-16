__all__ = (
    'aeApiCreate',
    'aeApiFree',
    'aeApiAddEvent',
    'aeApiDelEvent',
    'aeApiPoll',
    'aeApiName',
    'aeApiResize',
)

import select
import typing
import socket
from typing import Optional as Opt, List, Union


if typing.TYPE_CHECKING:
    from .ae import aeEventLoop, timeval

class aeApiState:
    def __init__(self):
        self.rfds: List[int] = []
        self.wfds: List[int] = []
        # self._rfds: List[int] = []
        # self._wfds: List[int] = []

FD_SETSIZE = 1024

### public api ###

def aeApiCreate(eventLoop: 'aeEventLoop') -> int:
    state = aeApiState()
    eventLoop.apidata = state
    return 0

def aeApiFree(eventLoop: 'aeEventLoop') -> None:
    del eventLoop

def aeApiAddEvent(eventLoop: 'aeEventLoop', fd: int, mask: int) -> int:
    from .ae import AE_READABLE, AE_WRITABLE
    state: aeApiState = eventLoop.apidata
    if mask & AE_READABLE:
        state.rfds.append(fd)
    if mask & AE_WRITABLE:
        state.wfds.append(fd)
    return 0

def aeApiDelEvent(eventLoop: 'aeEventLoop', fd: int, mask: int) -> None:
    from .ae import AE_READABLE, AE_WRITABLE
    state: aeApiState = eventLoop.apidata
    if mask & AE_READABLE:
        list_remove(state.rfds, fd)
    if mask & AE_WRITABLE:
        list_remove(state.wfds, fd)


def aeApiPoll(eventLoop: 'aeEventLoop', tvp: Opt['timeval']) -> int:
    from .ae import AE_READABLE, AE_WRITABLE, AE_NONE
    assert tvp
    numevents = 0
    state: aeApiState = eventLoop.apidata

    timeout = tvp.time
    _rfds, _wfds, _ = select.select(state.rfds, state.wfds, [], timeout)
    if _rfds or _wfds:
        for j in range(eventLoop.maxfd):
            mask = 0
            fe = eventLoop.events[j]
            if fe.mask == AE_NONE:
                continue
            if (fe.mask & AE_READABLE) and (j in _rfds):
                mask |= AE_READABLE
            if (fe.mask & AE_WRITABLE) and (j in _wfds):
                mask |= AE_WRITABLE
            eventLoop.fired[numevents].fd = j
            eventLoop.fired[numevents].mask = mask
            numevents += 1
    return numevents


def aeApiName() -> str:
    return "select"

def aeApiResize(eventLoop: 'aeEventLoop', setsize: int) -> int:
    if setsize >= FD_SETSIZE:
        return -1
    return 0

def list_remove(l: list, elem):
    try:
        idx = l.index(elem)
        l.remove(idx)
    except ValueError:
        pass
