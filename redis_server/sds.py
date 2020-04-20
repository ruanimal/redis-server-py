# -*- coding:utf-8 -*-

from typing import Union
from array import array


# class cstr(array):
#     def __init__(self, init:Optional[bytes, bytearray]=b''):
#         super().__init__('b', init.rstrip(b'\0'))
#         self.append(b'\0')

#     def length(self):
#         return len(self) - 1

cstr = Union[bytearray, bytes]

class Sdshdr(object):
    def __init__(self, length: int, free: int, buf: array):
        self.len = length
        self.free = free
        self.buf = buf

    def __iter__(self):
        return iter(self.buf)

def sdsnewlen(init: cstr, initlen: int) -> Sdshdr:
    # buf = array('b', (init[i] if i < len(init) else None for i in range(initlen)))
    # buf[initlen] = 0   # b'\0'
    buf = array('b', init)
    buf.append(0)
    sh = Sdshdr(initlen, 0, buf)
    return sh

def sdsempty() -> Sdshdr:
    return sdsnewlen(b'', 0)

def sdsnew(init: cstr):
    return sdsnewlen(init, len(init))

if __name__ == "__main__":
    s = Sdshdr(3, 0, array('b', b'111'))
