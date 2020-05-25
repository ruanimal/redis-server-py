from typing import NewType, Tuple, Optional as Opt
from .csix import *
from .endianconv import intrev32ifbe, memrev32ifbe

ZIPLIST_HEAD = 0
ZIPLIST_TAIL = 1

#  ziplist 末端标识符，以及 5 字节长长度标识符
ZIP_END = 255
ZIP_BIGLEN = 254

# 字符串编码和整数编码的掩码
ZIP_STR_MASK = 0xc0          # 0b11000000
ZIP_INT_MASK = 0x30          # 0b00110000

# 字符串编码类型
ZIP_STR_06B = (0 << 6)       # 0b00000000
ZIP_STR_14B = (1 << 6)       # 0b01000000
ZIP_STR_32B = (2 << 6)       # 0b10000000

# 整数编码类型
ZIP_INT_16B = (0xc0 | 0<<4)  # 0b11000000
ZIP_INT_32B = (0xc0 | 1<<4)  # 0b11010000
ZIP_INT_64B = (0xc0 | 2<<4)  # 0b11100000
ZIP_INT_24B = (0xc0 | 3<<4)  # 0b11110000
ZIP_INT_8B = 0xfe            # 0b11111110

# 4 位整数编码的掩码和类型
ZIP_INT_IMM_MASK = 0x0f      # 0b00001111
ZIP_INT_IMM_MIN = 0xf1       # 0b11110001
ZIP_INT_IMM_MAX = 0xfd       # 0b11111101
ZIP_INT_IMM_VAL = lambda v: v & ZIP_INT_IMM_MASK

# 24 位整数的最大值和最小值
INT24_MAX = 0x7fffff
INT24_MIN = (-INT24_MAX - 1)

# 查看给定编码 enc 是否字符串编码
ZIP_IS_STR = lambda enc: ((enc & ZIP_STR_MASK) < ZIP_STR_MASK)

# 定位到 ziplist 的 bytes 属性，该属性记录了整个 ziplist 所占用的内存字节数
# 用于取出 bytes 属性的现有值，或者为 bytes 属性赋予新值
#define ZIPLIST_BYTES(zl)       (*((uint32_t*)(zl)))
# 定位到 ziplist 的 offset 属性，该属性记录了到达表尾节点的偏移量
# 用于取出 offset 属性的现有值，或者为 offset 属性赋予新值
#define ZIPLIST_TAIL_OFFSET(zl) (*((uint32_t*)((zl)+sizeof(uint32_t))))
# 定位到 ziplist 的 length 属性，该属性记录了 ziplist 包含的节点数量
# 用于取出 length 属性的现有值，或者为 length 属性赋予新值
#define ZIPLIST_LENGTH(zl)      (*((uint16_t*)((zl)+sizeof(uint32_t)*2)))
# 返回 ziplist 表头的大小
ZIPLIST_HEADER_SIZE = 4 + 4 + 2
# 返回指向 ziplist 第一个节点（的起始位置）的指针
#define ZIPLIST_ENTRY_HEAD(zl)  ((zl)+ZIPLIST_HEADER_SIZE)
# 返回指向 ziplist 最后一个节点（的起始位置）的指针
#define ZIPLIST_ENTRY_TAIL(zl)  ((zl)+intrev32ifbe(ZIPLIST_TAIL_OFFSET(zl)))
# 返回指向 ziplist 末端 ZIP_END （的起始位置）的指针
#define ZIPLIST_ENTRY_END(zl)   ((zl)+intrev32ifbe(ZIPLIST_BYTES(zl))-1)


def ziplist_bytes(zl: 'ziplist') -> int:
    return zl.zlbytes

def ziplist_tail_offset(zl: 'ziplist') -> int:
    return zl.zltail

def ziplist_length(zl: 'ziplist') -> int:
    return zl.zllen

def ziplist_entry_tail(zl: 'ziplist') -> int:
    return zl.zltail

def ziplist_entry_head(zl: 'ziplist') -> cstrptr:
    return cstrptr(zl, pos=ZIPLIST_HEADER_SIZE)

def ziplist_entry_end(zl: 'ziplist') -> cstrptr:
    return cstrptr(zl, pos=zl.zlbytes-1)
# /*
#  * 增加 ziplist 的节点数
#  *
#  * T = O(1)
#  */
# #define ZIPLIST_INCR_LENGTH(zl,incr) { \
#     if (ZIPLIST_LENGTH(zl) < UINT16_MAX) \
#         ZIPLIST_LENGTH(zl) = intrev16ifbe(intrev16ifbe(ZIPLIST_LENGTH(zl))+incr); \
# }

class zlentry:
    __fmt__ = 'IIIIIBI'

    def __init__(self):
        self.prevrawlensize: int = None
        self.prevrawlen: int = None
        self.lensize: int = None
        self.len: int = None
        self.headersize: int = None
        self.encoding: int = None
        self.p = None

class ziplist(bytearray):
    def __init__(self):
        super().__init__([0 for _ in range(4 + 4 + 2 + 1)])
        self.zlbytes: int = intrev32ifbe(len(self))
        self.zltail: int = intrev32ifbe(self.zlbytes-1)
        self.zllen: int = 0
        self[-1] = 255

    @property
    def zlend(self):
        return self[-1]


#  * 从 ptr 中取出节点值的编码类型，并将它保存到 encoding 变量中。
#  *
#  * T = O(1)
#  */
# #define ZIP_ENTRY_ENCODING(ptr, encoding) do {  \
#     (encoding) = (ptr[0]); \
#     if ((encoding) < ZIP_STR_MASK) (encoding) &= ZIP_STR_MASK; \
# } while(0)

def zip_decode_prevlensize(p: cstrptr) -> int:
    if p.buf[p.pos] < ZIP_BIGLEN:
        return 1
    else:
        return 5

def zip_decode_prevlen(p: cstrptr) -> Tuple[int, int]:
    prevlensize = zip_decode_prevlensize(p)
    prevlen = 0
    if prevlensize == 1:
        prevlen = p.buf[p.pos]
    elif prevlensize == 5:
        prevlen = cstr2uint32(p.buf[p.pos+1: p.pos+5])
        prevlen = intrev32ifbe(prevlen)
    else:
        raise ValueError
    return prevlensize, prevlen

def zip_entry_encoding(p: cstrptr) -> int:
    encoding = cstr2int(p.buf[p.pos: p.pos+1], 'uint8')
    assert encoding < ZIP_STR_MASK
    return encoding & ZIP_STR_MASK

def zip_decode_length(p: cstrptr) -> Tuple[int, int, int]:
    encoding = zip_entry_encoding(p)
    lensize = 0
    length = 0
    if encoding < ZIP_STR_MASK:
        if encoding == ZIP_STR_06B:
            lensize = 1
            length = p.buf[p.pos] & 0x3f
        elif encoding == ZIP_STR_14B:
            lensize = 2
            length = cstr2int(p.buf[p.pos:p.pos+2], 'uint16')
        elif encoding == ZIP_STR_32B:
            lensize = 5
            length = cstr2int(p.buf[p.pos+1:p.pos+5], 'uint32')
        else:
            raise ValueError
    else:
        lensize = 1
        length = zipIntSize(encoding)
    return encoding, lensize, length

def zipIntSize(encoding: int) -> int:
    mapping = {
        ZIP_INT_8B:  1,
        ZIP_INT_16B: 2,
        ZIP_INT_24B: 3,
        ZIP_INT_32B: 4,
        ZIP_INT_64B: 8,
    }
    return mapping[encoding]

def ziplistNew() -> ziplist:
    return ziplist()

def zipEntry(p: cstrptr) -> zlentry:
    e = zlentry()
    e.prevrawlensize, e.prevrawlen = zip_decode_prevlen(p)
    e.encoding, e.lensize, e.len = zip_decode_length(p)
    e.headersize = e.prevrawlensize + e.lensize
    e.p = c_assignment(p)
    return e

def zipRawEntryLength(p: cstrptr):
    prevlensize = zip_decode_prevlensize(p)
    encoding, lensize, length = zip_decode_length(p.new(p.pos+prevlensize))
    return prevlensize + lensize + length

def zipTryEncoding(entry: cstr, entrylen: int, v: intptr, encoding: intptr) -> int:
    if entrylen >= 32 or encoding == 0:
        return 0

    value = 0
    try:
        value = int(entry[:entrylen])
    except ValueError:
        return 0

    if 0 <= value <= 12:
        enc = ZIP_INT_IMM_MIN + value
    elif INT8_MIN <= value <= INT8_MAX:
        enc = ZIP_INT_8B
    elif INT16_MIN <= value <= INT16_MAX:
        enc = ZIP_INT_16B
    elif INT32_MIN <= value <= INT32_MAX:
        enc = ZIP_INT_32B
    else:
        enc = ZIP_INT_64B
    v.value = value
    encoding.value = enc
    return 1

def zipPrevEncodeLength(p: Opt[cstrptr], length: int) -> int:
    if p is None:
        return length < ZIP_BIGLEN and 1 or 4 + 1  # sizeof(unsigned int) + 1

    if length < ZIP_BIGLEN:
        p.buf[p.pos] = length
        return 1
    else:
        p.buf[p.pos] = ZIP_BIGLEN
        p.buf[p.pos+1:p.pos+5] = int2cstr(length, 'uint32')
        memrev32ifbe(p.buf, p.pos+1)
        return 1 + 4

def zipPrevEncodeLengthForceLarge(p: Opt[cstrptr], length: int) -> None:
    if p is None:
        return
    p.buf[p.pos] = ZIP_BIGLEN
    p.buf[p.pos+1:p.pos+5] = int2cstr(length, 'uint32')
    memrev32ifbe(p.buf, p.pos+1)

def zipEncodeLength(p: Opt[cstrptr], encoding: int, rawlen: int) -> int:
    length = 1
    buf = bytearray(0 for _ in range(5))
    if ZIP_IS_STR(encoding):
        if rawlen <= 0x3f:
            if not p:
                return length
            buf[0] = ZIP_STR_06B | rawlen
        elif rawlen <= 0x3fff:
            length += 1
            if not p:
                return length
            buf[0] = ZIP_STR_14B | ((rawlen >> 8) & 0x3f)
            buf[1] = rawlen & 0xff
        else:
            length += 4
            if not p:
                return length
            buf[0] = ZIP_STR_32B
            buf[1] = (rawlen >> 24) & 0xff
            buf[2] = (rawlen >> 16) & 0xff
            buf[3] = (rawlen >> 8) & 0xff
            buf[4] = rawlen & 0xff
    else:
        if not p:
            return length
        buf[0] = encoding
    p.buf[p.pos:p.pos+length] = buf[:length]
    return length

def __ziplistInsert(zl: ziplist, p: cstrptr, s: cstr, slen: int):
    curlen = intrev32ifbe(zl.zlbytes)
    reqlen = 0
    prevlen = 0
    encoding_p = intptr(0)
    value_p = intptr(123456789)

    if p.buf[p.pos] != ZIP_END:
        entry = zipEntry(p)
        prevlen = entry.prevrawlen
    else:
        ptail = p.new(ziplist_entry_tail(zl))
        if ptail.buf[p.pos] != ZIP_END:
            prevlen = zipRawEntryLength(p)

    if zipTryEncoding(s, slen, value_p, encoding_p):
        reqlen = zipIntSize(encoding_p.value)
    else:
        reqlen = slen

    reqlen += zipPrevEncodeLength(None, prevlen)
    reqlen += zipEncodeLength(None, encoding_p.value, slen)


def ziplistPush(zl: ziplist, s: cstr, slen: int, where: int):
    p = (where == ZIPLIST_HEAD) and ziplist_entry_head(zl) or ziplist_entry_end(zl)
    return __ziplistInsert(zl, p, s, slen)

# unsigned char *ziplistNew(void);
# unsigned char *ziplistPush(unsigned char *zl, unsigned char *s, unsigned int slen, int where);
# unsigned char *ziplistIndex(unsigned char *zl, int index);
# unsigned char *ziplistNext(unsigned char *zl, unsigned char *p);
# unsigned char *ziplistPrev(unsigned char *zl, unsigned char *p);
# unsigned int ziplistGet(unsigned char *p, unsigned char **sval, unsigned int *slen, long long *lval);
# unsigned char *ziplistInsert(unsigned char *zl, unsigned char *p, unsigned char *s, unsigned int slen);
# unsigned char *ziplistDelete(unsigned char *zl, unsigned char **p);
# unsigned char *ziplistDeleteRange(unsigned char *zl, unsigned int index, unsigned int num);
# unsigned int ziplistCompare(unsigned char *p, unsigned char *s, unsigned int slen);
# unsigned char *ziplistFind(unsigned char *p, unsigned char *vstr, unsigned int vlen, unsigned int skip);
# unsigned int ziplistLen(unsigned char *zl);
# size_t ziplistBlobLen(unsigned char *zl);
