# -*- coding:utf-8 -*-

from math import isnan
from typing import Any, Union, Callable, Optional as Opt, List
from .robject import decrRefCount, robj, compareStringObjects, equalStringObjects
from .csix import *

ZSKIPLIST_MAXLEVEL = 32
ZSKIPLIST_P = 0.25

class zskiplistLevel:
    def __init__(self):
        self.forward: zskiplistNode = None
        self.span: int = 0

class zskiplistNode:
    def __init__(self):
        self.obj: robj = None
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
    # headNode don't need obj and score
    zsl.header = zslCreateNode(ZSKIPLIST_MAXLEVEL, 0, None)   # type: ignore
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

def _node_lt(node: zskiplistNode, score: float, obj: robj):
    if node.score < score:
        return True
    if (node.score == score and
        compareStringObjects(node.obj, obj) < 0):
        return True
    return False

def zslInsert(zsl: zskiplist, score: float, obj: robj) -> zskiplistNode:
    assert not isnan(score)
    update: List[Opt[zskiplistNode]] = [None for _ in range(ZSKIPLIST_MAXLEVEL)]
    # rank[i]: 到第i层为止经过的所有node的span总和
    rank = [0 for _ in range(ZSKIPLIST_MAXLEVEL)]
    x = zsl.header
    # 从高层开始遍历
    for i in range(zsl.level-1, -1, -1):
        rank[i] = 0 if i == zsl.level-1 else rank[i+1]
        while x.level[i].forward and _node_lt(x.level[i].forward, score, obj):
            rank[i] += x.level[i].span
            x = x.level[i].forward
        # 每一层, 小于新Node的最大Node, 新节点会插入到update[i].level[i]之后
        update[i] = x

    level = zslRandomLevel()
    if level > zsl.level:
        # 从头部扩展level, 新level的跨度等于跳表长度
        for i in range(zsl.level, level):
            rank[i] = 0
            update[i] = zsl.header
            update[i].level[i].span = zsl.length # type: ignore
        zsl.level = level

    x = zslCreateNode(level, score, obj)
    for i in range(level):
        x.level[i].forward = update[i].level[i].forward  # type: ignore
        update[i].level[i].forward = x  # type: ignore
        x.level[i].span = update[i].level[i].span - (rank[0] - rank[i])  # type: ignore
        update[i].level[i].span = (rank[0] - rank[i]) + 1  # type: ignore

    for i in range(level, zsl.level):
        update[i].level[i].span += 1  # type: ignore

    # 设置新节点的后退指针, level[0]才有后退指针
    x.backward = None if update[0] == zsl.header else update[0]
    if x.level[0].forward:
        x.level[0].forward.backward = x
    else:
        zsl.tail = x

    zsl.length += 1
    return x


def zslDeleteNode(zsl: zskiplist, x: zskiplistNode, update: List[Opt[zskiplistNode]]) -> None:
    for i in range(zsl.level):
        if update[i].level[i].forward == x:  # type: ignore
            update[i].level[i].span += x.level[i].span - 1  # type: ignore
            update[i].level[i].forward = x.level[i].forward  # type: ignore
        else:
            update[i].level[i].span -= 1  # type: ignore

    if x.level[0].forward:  # 不是最后一个节点
        x.level[0].forward.backward = x.backward
    else:
        zsl.tail = x.backward  # type: ignore

    # 如果被删除的节点level最大, 则头节点的倒数第二level的forward就会是None
    while zsl.level > 1 and zsl.header.level[zsl.level-1].forward == None:
        zsl.level -= 1
    zsl.length -= 1


def zslDelete(zsl: zskiplist, score: float, obj: robj) -> int:
    update: List[Opt[zskiplistNode]] = [None for _ in range(ZSKIPLIST_MAXLEVEL)]
    x = zsl.header
    # 从高层开始遍历
    for i in range(zsl.level-1, -1, -1):
        while x.level[i].forward and _node_lt(x.level[i].forward, score, obj):
            x = x.level[i].forward
        # 每一层, 小于新Node的最大Node, 新节点会插入到update[i].level[i]之后
        update[i] = x

    # 此时的x是待删除节点的前一个节点
    x = x.level[0].forward
    if x and score == x.score and equalStringObjects(x.obj, obj):
        zslDeleteNode(zsl, x, update)
        zslFreeNode(x)
        return 1
    else:
        return 0
    return 0


def zslGetRank(zsl: zskiplist, score: float, obj: robj) -> int:
    rank = 0
    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while x.level[i].forward and _node_lt(x.level[i].forward, score, obj):
            rank += x.level[i].span
            x = x.level[i].forward
        if x.obj and equalStringObjects(x.obj, obj):
            return rank
    return 0


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
