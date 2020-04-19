# -*- coding:utf-8 -*-

from typing import Optional
from array import array

class Sdshdr(array):
    def __init__(self, len: int, fee: int, buf: array):
        self.len = len
        self.free = free
        super().__init__('b', array)

def sdsnewlen(init: bytes, initlen: int) -> Sdshdr:
    buf = array('b', init)
    buf.append(b'\x00')
    sh = Sdshdr(initlen, 0, buf)
    return sh

def sdsempty() -> Sdshdr:
    return sdsnewlen(b'', 0)

def sdsnew(init: Optional[bytes]=b''):
    return sdsnewlen(init, len(init))

