__all__ = (
    'aeApiCreate',
    'aeApiFree',
    'aeApiAddEvent',
    'aeApiDelEvent',
    'aeApiPoll',
    'aeApiName',
    'aeApiResize',
)

import logging
import select
import typing
import socket
from typing import Optional as Opt, List, Union, Set

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from .ae import aeEventLoop, timeval

class aeApiState:
    def __init__(self):
        self.rfds: Set[int] = set()
        self.wfds: Set[int] = set()
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
        state.rfds.add(fd)
    if mask & AE_WRITABLE:
        state.wfds.add(fd)
    return 0

def aeApiDelEvent(eventLoop: 'aeEventLoop', fd: int, mask: int) -> None:
    from .ae import AE_READABLE, AE_WRITABLE
    state: aeApiState = eventLoop.apidata
    if mask & AE_READABLE and fd in state.rfds:
        state.rfds.remove(fd)
    if mask & AE_WRITABLE and fd in state.wfds:
        state.wfds.remove(fd)

def aeApiPoll(eventLoop: 'aeEventLoop', tvp: Opt['timeval']) -> int:
    from itertools import chain
    from .ae import AE_READABLE, AE_WRITABLE, AE_NONE

    assert tvp
    numevents = 0
    state: aeApiState = eventLoop.apidata

    timeout = tvp.time
    _rfds, _wfds, _ = select.select(state.rfds, state.wfds, [], timeout)
    _rfds_set = set(_rfds)
    _wfds_set = set(_wfds)
    fd = 0
    for fd in range(eventLoop.maxfd+1):
        mask = 0
        fe = eventLoop.events[fd]
        if fe.mask == AE_NONE:
            continue
        if (fe.mask & AE_READABLE) and fd in _rfds_set:
            mask |= AE_READABLE
        if (fe.mask & AE_WRITABLE) and fd in _wfds_set:
            mask |= AE_WRITABLE
        eventLoop.fired[numevents].fd = fd
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
