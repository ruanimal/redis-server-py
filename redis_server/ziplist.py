from typing import NewType
from .csix import *

ziplist = NewType('ziplist', bytearray)

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
#define ZIPLIST_HEADER_SIZE     (sizeof(uint32_t)*2+sizeof(uint16_t))
# 返回指向 ziplist 第一个节点（的起始位置）的指针
#define ZIPLIST_ENTRY_HEAD(zl)  ((zl)+ZIPLIST_HEADER_SIZE)
# 返回指向 ziplist 最后一个节点（的起始位置）的指针
#define ZIPLIST_ENTRY_TAIL(zl)  ((zl)+intrev32ifbe(ZIPLIST_TAIL_OFFSET(zl)))
# 返回指向 ziplist 末端 ZIP_END （的起始位置）的指针
#define ZIPLIST_ENTRY_END(zl)   ((zl)+intrev32ifbe(ZIPLIST_BYTES(zl))-1)

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
    def __init__(self):
        self.prevrawlensize: int = None
        self.prevrawlen: int = None
        self.lensize: int = None
        self.len: int = None
        self.headersize: int = None
        self.encoding: int = None
        self.p = None

#  * 从 ptr 中取出节点值的编码类型，并将它保存到 encoding 变量中。
#  *
#  * T = O(1)
#  */
# #define ZIP_ENTRY_ENCODING(ptr, encoding) do {  \
#     (encoding) = (ptr[0]); \
#     if ((encoding) < ZIP_STR_MASK) (encoding) &= ZIP_STR_MASK; \
# } while(0)

def zip_entry_encoding(zl: ziplist, pos: int):
    encoding = cstr2int(zl[pos:pos+1], 'uint8')
    assert encoding < ZIP_STR_MASK
    return encoding & ZIP_STR_MASK

def zipIntSize(encoding):
    mapping = {
        ZIP_INT_8B:  1,
        ZIP_INT_16B: 2,
        ZIP_INT_24B: 3,
        ZIP_INT_32B: 4,
        ZIP_INT_64B: 8,
    }
    return mapping[encoding]

def ziplistNew() -> ziplist:
    pass

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
