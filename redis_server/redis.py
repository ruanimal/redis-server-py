# -*- coding:utf-8 -*-

from typing import Any, Union, Callable, Optional as Opt, List
from .robject import decrRefCount
from .csix import *

REDIS_LRU_BITS = 24
ZSKIPLIST_MAXLEVEL = 32
ZSKIPLIST_P = 0.25

class redisObject:
    def __init__(self):
        self.type: int = 0
        self.encoding: int = 0
        self.lru: int = REDIS_LRU_BITS
        self.refcount: int = 0
        self.ptr = None

class zskiplistLevel:
    def __init__(self):
        self.forward: Opt[zskiplistNode] = None
        self.span: int = 0

class zskiplistNode:
    def __init__(self):
        self.obj: Opt[redisObject] = None
        self.score: float = 0
        self.backward: Opt[zskiplistNode] = None
        self.level: List[zskiplistLevel] = []

class zskiplist:
    def __init__(self):
        self.header: zskiplistNode = None
        self.tail: zskiplistNode = None
        self.length: int = 0
        self.level: int = 0

def zslCreate() -> zskiplist:
    zsl = zskiplist()
    zsl.level = 1
    zsl.length = 0
    zsl.header = zslCreateNode(ZSKIPLIST_MAXLEVEL, 0, None)
    return zsl

def zslCreateNode(level: int, score: float, obj) -> zskiplistNode:
    zn = zskiplistNode()
    zn.level = [zskiplistLevel() for _ in range(level)]
    zn.score = score
    zn.obj = obj
    return zn

def zslFreeNode(node: zskiplistNode) -> None:
    decrRefCount(node.obj)
    zfree(node)

def zslFree(zsl: zskiplist) -> None:
    node = zsl.header.level[0].forward
    zfree(zsl.header)
    while node:
        next_ = node.level[0].forward
        zslFreeNode(node)
        node = next_
    zfree(zsl)

# unsigned char *zzlInsert(unsigned char *zl, robj *ele, double score);
# int zslDelete(zskiplist *zsl, double score, robj *obj);
# zskiplistNode *zslFirstInRange(zskiplist *zsl, zrangespec *range);
# zskiplistNode *zslLastInRange(zskiplist *zsl, zrangespec *range);
# double zzlGetScore(unsigned char *sptr);
# void zzlNext(unsigned char *zl, unsigned char **eptr, unsigned char **sptr);
# void zzlPrev(unsigned char *zl, unsigned char **eptr, unsigned char **sptr);
# unsigned int zsetLength(robj *zobj);
# void zsetConvert(robj *zobj, int encoding);
# unsigned long zslGetRank(zskiplist *zsl, double score, robj *o);
