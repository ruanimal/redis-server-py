# -*- coding:utf-8 -*-

from math import isnan
from typing import Any, Union, Callable, Optional as Opt, List
from .robject import decrRefCount, robj, compareStringObjects
from .csix import *

ZSKIPLIST_MAXLEVEL = 32
ZSKIPLIST_P = 0.25

class zskiplistLevel:
    def __init__(self):
        self.forward: Opt[zskiplistNode] = None
        self.span: int = 0

class zskiplistNode:
    def __init__(self):
        self.obj: Opt[robj] = None
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

def zslCreateNode(level: int, score: float, obj: robj) -> zskiplistNode:
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

def zslInsert(zsl: zskiplist, score: float, obj: robj) -> zskiplistNode:
    assert not isnan(score)

    update = [None for _ in range(ZSKIPLIST_MAXLEVEL)]
    rank = [0 for _ in range(ZSKIPLIST_MAXLEVEL)]
    x = zsl.header
    for i in range(zsl.length-1, -1, -1):
        rank[i] = 0 if i == zsl.level-1 else rank[i+1]
        while x.level[i].forward and (
            x.level[i].forward.score < score or (
                x.level[i].forward.score == score and
                compareStringObjects(x.level[i].forward.obj, obj) < 0)):
            rank[i] += x.level[i].span
            x = x.level[i].forward
        update[i] = x

    level = zslRandomLevel()
    if level > zsl.level:
        for i in range(zsl.length, level, -1):
            rank[i] = 0
            update[i] = zsl.header
            update[i].level[i].span = zsl.length
        zsl.level = level
    x = zslCreateNode(level, score, obj)

    for i in range(level):
        x.level[i].forward = update[i].level[i].forward
        update[i].level[i].forward = x
        x.level[i].span = update[i].level[i].span - (rank[0] - rank[i])
        update[i].level[i].span = (rank[0] - rank[i]) + 1

    for i in range(level, zsl.level):
        update[i].level[i].span += 1

    x.backward = None if update[0] == zsl.header else update[0]
    if x.level[0].forward:
        x.level[0].forward.backward = x
    else:
        zsl.tail = x

    zsl.length += 1
    return x

def zslRandomLevel() -> int:
    level = 1
    while (c_random() & 0xFFFF) < (ZSKIPLIST_P * 0xFFFF):
        level += 1
    return level if level < ZSKIPLIST_MAXLEVEL else ZSKIPLIST_MAXLEVEL

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
