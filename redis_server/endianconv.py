import sys
from .csix import int2cstr, cstr2int

LITTLE_ENDIAN = 'little'
BIG_ENDIAN = 'big'

def memrev16(buf: bytearray, offset: int=0):
    assert offset < len(buf)

    buf[offset:offset+2] = buf[offset:offset+2][::-1]

def memrev32(buf: bytearray, offset: int=0):
    assert offset < len(buf)

    buf[offset:offset+4] = buf[offset:offset+4][::-1]

def memrev64(buf: bytearray, offset: int=0):
    assert offset < len(buf)

    buf[offset:offset+8] = buf[offset:offset+8][::-1]

def intrev16(v: int) -> int:
    bin_v = bytearray(int2cstr(v, 'uint16'))
    memrev16(bin_v)
    return cstr2int(bin_v, 'uint16')

def intrev32(v: int) -> int:
    bin_v = bytearray(int2cstr(v, 'uint32'))
    memrev32(bin_v)
    return cstr2int(bin_v, 'uint32')

def intrev64(v: int) -> int:
    bin_v = bytearray(int2cstr(v, 'uint64'))
    memrev64(bin_v)
    return cstr2int(bin_v, 'uint64')

if sys.byteorder == LITTLE_ENDIAN:
    memrev16ifbe = lambda p: None
    memrev32ifbe = lambda p: None
    memrev64ifbe = lambda p: None
    intrev16ifbe = lambda v: v
    intrev32ifbe = lambda v: v
    intrev64ifbe = lambda v: v
else:
    memrev16ifbe = memrev16
    memrev32ifbe = memrev32
    memrev64ifbe = memrev64
    intrev16ifbe = intrev16
    intrev32ifbe = intrev32
    intrev64ifbe = intrev64
