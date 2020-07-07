import socket
import typing
from .csix import cstr, memcpy, NUL
from typing import Dict, Any

if typing.TYPE_CHECKING:
    from .redis import RedisServer

def ll2string(s: bytearray, length: int, value: int) -> int:
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
    s[:l] = buf[p:p+l]  # memcpy(s,p,l)
    s[l] = NUL
    return l


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

def get_server() -> 'RedisServer':
    from .redis import RedisServer
    return RedisServer()
