import socket
import typing
from .csix import cstr, memcpy, NUL, LONG_MIN, LONG_MAX
from typing import Dict, Any, Union, ByteString, Tuple

if typing.TYPE_CHECKING:
    from .redis import RedisServer, sharedObjects

def ll2string(s: ByteString, length: int, value: int) -> int:
    if length == 0:
        return 0

    buf = bytearray(32)
    v = -value if value < 0 else value
    p = 31
    while True:
        buf[p] = ord('0') + (v % 10)
        p -= 1
        v //= 10
        if not v:
            break
    if (value < 0):
        buf[p] = ord('-')
        p -= 1
    p += 1
    l = 32 - p
    if l+1 > length:
        l = length - 1
    s[:l] = buf[p:p+l]  # type: ignore
    s[l] = NUL  # type: ignore
    return l

def string2l(s: cstr, slen: int) -> Tuple[int, int]:
    """convert bytes to int
    return:
        flag: 1 -> succ, 0 -> fail
        val: int value
    """
    val = 0
    try:
        val = int(s[:slen].strip(b'\0'))
    except ValueError:
        return 0, 0
    if val < LONG_MIN:
        return 0, 0
    elif val > LONG_MAX:
        return 0, 0
    else:
        return 1, val

string2ll = string2l


class _SingletonMeta(type):
    _instances: Dict[Any, Any]  = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(metaclass=_SingletonMeta):
    pass

class SocketCache:
    """socket cache, convert socket fileno to socket object"""

    _cache: Dict[int, socket.socket] = {}

    @classmethod
    def get(cls, fileno: int):
        return cls._cache[fileno]

    @classmethod
    def set(cls, sock: socket.socket):
        assert sock.fileno() not in cls._cache
        cls._cache[sock.fileno()] = sock

def zmalloc_used_memory() -> int:
    # TODO(rlj): something to do.
    return 0

def get_server() -> 'RedisServer':
    from .redis import RedisServer
    return RedisServer()

def get_shared() -> 'sharedObjects':
    from .redis import sharedObjects
    return sharedObjects()
