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
# C语言 \0
NUL = 0
# SDS最大预分配长度
SDS_MAX_PREALLOC = (1024*1024)

def strlen(string: cstr) -> int:
    res = 0
    for i in string:
        if i == NUL:
            break
        res += 1
    return res


class Sdshdr(object):
    def __init__(self, length: int, free: int, buf: array):
        self.len = length
        self.free = free
        self.buf = buf

    def __repr__(self):
        return 'Sdshdr({}, {}, {!r})'.format(self.len, self.free, self.buf)

    def __iter__(self):
        return self.buf.__iter__()

    def __getitem__(self, key):
        return self.buf.__getitem__(key)

    def __setitem__(self, key, value):
        return self.buf.__setitem__(key, value)

    def __delitem__(self, key):
        return self.buf.__delitem__(key)

    # def __missing__(self, key):
    #     return self.buf.__missing__(key)

sds = Sdshdr

def sdsnewlen(init: cstr, initlen: int) -> sds:
    # buf = array('b', (init[i] if i < len(init) else None for i in range(initlen)))
    # buf[initlen] = 0   # b'\0'
    buf = array('b', init)
    buf.append(NUL)
    sh = sds(initlen, 0, buf)
    return sh

def sdsempty() -> sds:
    return sdsnewlen(b'', 0)

def sdsnew(init: cstr) -> sds:
    return sdsnewlen(init, len(init))

def sdsfree(s: sds) -> None:
    del s

def sdsupdatelen(s: sds) -> None:
    raise NotImplementedError

def sdsclear(s: sds) -> None:
    s.free += s.len
    s.len = 0
    s.buf[0] = NUL

def sdsavail(s: sds) -> int:
    return s.free

def sdslen(s: sds) -> int:
    return s.len

def sdsMakeRoomFor(s: sds, addlen: int) -> sds:
    free = sdsavail(s)
    if free >= addlen:
        return s

    len_ = sdslen(s)
    newlen = len_ + addlen
    if newlen < SDS_MAX_PREALLOC:
        newlen *= 2
    else:
        newlen += SDS_MAX_PREALLOC
    s.buf.extend((NUL for _ in range(newlen - len_)))  # NOTE 默认填错NUL, 和c实现有所不同
    s.free = newlen - len_
    return s

def sdsRemoveFreeSpace(s: sds) -> sds:
    s[s.len+1:] = []
    s.free = 0
    return s

def sdsAllocSize(s: sds):
    # NOTE not malloc in python
    raise NotImplementedError

def sdsIncrLen(s: sds, incr: int) -> None:
    assert s.free >= incr
    s.len += incr
    s.free -= incr

    assert s.free >= 0
    s[s.len] = NUL


sdsgrowzero = sdsMakeRoomFor

def sdscatlen(s: sds, t: Union[cstr, sds], len_: int):
    curlen = sdslen(s)
    s = sdsMakeRoomFor(s, len_)
    s[curlen:len_] = t[:len_]
    s.len = curlen + len_
    s.free = s.free - len_
    s[curlen+len_] = NUL
    return s

def sdscat(s: sds, t: cstr) -> sds:
    return sdscatlen(s, t, strlen(t))

def sdscatsds(s: sds, t: sds) -> sds:
    return sdscatlen(s, t, sdslen(t))

def sdscpylen(s: sds, t: cstr, len_: int) -> sds:
    totlen = s.free + s.len
    if totlen < len_:
        s = sdsMakeRoomFor(s, len_ - s.len)
        totlen = s.free + s.len

    s[:len_] = t[:len_]
    s[len_] = NUL
    s.len = len_
    s.free = totlen - len_
    return s

def sdscpy(s: sds, t: cstr) -> sds:
    return sdscpylen(s, t, strlen(t))

# long long 数值转成字符串后的长度
# SDS_LLSTR_SIZE = 21  # NOTE no need in python
def sdsfromlonglong(value: int) -> sds:
    buf = str(value).encode()
    return sdsnewlen(buf, len(buf))

def sdscatprintf(s: sds, fmt: cstr, *args) -> sds:
    buf = fmt % args
    return sdscat(s, buf)

# This function is similar to sdscatprintf, but much faster as it does
# So I just make then same
sdscatfmt = sdscatprintf

def sdstrim(s: sds, cset: cstr) -> sds:
    tcset = set(cset)
    left, right = 0, sdslen(s)-1

    while left <= sdslen(s)-1 and s[left] in tcset: left += 1
    while right > 0 and s[right] in tcset: right -= 1

    length = 0 if (left > right) else (right - left + 1)
    if left > 0:
        s[:length] = s[left: left+length]
    s[length] = NUL
    s.free += (s.len - length)
    s.len = length
    return s

def sdsrange(s: sds, start: int, end: int) -> None:
    length = sdslen(s)
    if (length == 0):
        return
    if (start < 0):
        start = length+start
        if (start < 0):
            start = 0

    if (end < 0):
        end = length+end
        if (end < 0):
            end = 0

    newlen = 0 if (start > end) else (end-start)+1
    if (newlen != 0):
        if (start >= length):
            newlen = 0
        elif (end >= length):
            end = length-1
            newlen = 0 if (start > end) else (end-start)+1
    else:
        start = 0
    print(newlen)
    if (start and newlen):
        s[:newlen] = s[start: start+newlen]
    s[newlen] = NUL
    s.free += (s.len - newlen)
    s.len = newlen

def sdstolower(s: sds) -> None:
    s.buf[:] = s.buf.tobytes().lower()


if __name__ == "__main__":
    ss = Sdshdr(3, 0, array('b', b'111'))

