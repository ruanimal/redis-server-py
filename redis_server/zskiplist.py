# -*- coding:utf-8 -*-

from math import isnan
from typing import Any, Union, Callable, Optional as Opt, List
from .robject import decrRefCount, robj, compareStringObjects, equalStringObjects
from .csix import *
from .rdict import rDict, dictDelete

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

class zrangespec:
    def __init__(self):
        self.min: float = 0
        self.max: float = 0
        self.minex: int = 0
        self.maxex: int = 0


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
    # update list记录的是每一层, 新节点需要插入的位置(新节点x的backward节点指针)
    update: List[Opt[zskiplistNode]] = [None for _ in range(ZSKIPLIST_MAXLEVEL)]
    # rank[i]: 从高到低, 到第i层为止经过的所有node的span总和, 也就是节点的排序
    # 用于计算新节点各层的span, 以及新节点的后继节点各层的span
    rank = [0 for _ in range(ZSKIPLIST_MAXLEVEL)]
    x = zsl.header
    # 从高层开始遍历
    for i in range(zsl.level-1, -1, -1):
        rank[i] = 0 if i == zsl.level-1 else rank[i+1]
        # 找到每一层x需要插入的位置, 并更新rank
        while x.level[i].forward and _node_lt(x.level[i].forward, score, obj):
            rank[i] += x.level[i].span
            x = x.level[i].forward
        # 对于每一层i, 新节点会插入到update[i].level[i]之后
        update[i] = x

    level = zslRandomLevel()  # 取一个随机层数, 使zskiplist更为均衡
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


def zslGetElementByRank(zsl: zskiplist, rank: int) -> Opt[zskiplistNode]:
    traversed = 0
    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while x.level[i].forward and traversed + x.level[i].span <= rank:
            traversed += x.level[i].span
            x = x.level[i].forward
        if traversed == rank:
            return x
    return None


def zslRandomLevel() -> int:
    level = 1
    while (c_random() & 0xFFFF) < (ZSKIPLIST_P * 0xFFFF):
        level += 1
    return level if level < ZSKIPLIST_MAXLEVEL else ZSKIPLIST_MAXLEVEL

def zslValueGteMin(value: float, spec: zrangespec) -> int:
    return spec.minex and (value > spec.min) or (value >= spec.min)

def zslValueLteMax(value: float, spec: zrangespec) -> int:
    return spec.maxex and (value > spec.max) or (value >= spec.max)

def zslIsInRange(zsl: zskiplist, zrange: zrangespec) -> int:
    if zrange.min > zrange.max or (
        zrange.min == zrange.max and (
            zrange.minex or zrange.maxex)):
        return 0

    x = zsl.tail
    if x == None or (not zslValueGteMin(x.score, zrange)):
        return 0
    x = zsl.header.level[0].forward
    if x == None or (not zslValueLteMax(x.score, zrange)):
        return 0
    return 1

def zslFirstInRange(zsl: zskiplist, zrange: zrangespec) -> Opt[zskiplistNode]:
    if not zslIsInRange(zsl, zrange):
        return None
    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while (x.level[i].forward and
            not zslValueGteMin(x.level[i].forward.score, zrange)):
            x = x.level[i].forward
    x = x.level[0].forward
    assert x != None

    if not zslValueLteMax(x.score, zrange):
        return None
    return x

def zslLastInRange(zsl: zskiplist, zrange: zrangespec) -> Opt[zskiplistNode]:
    if not zslIsInRange(zsl, zrange):
        return None
    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while (x.level[i].forward and
            zslValueLteMax(x.level[i].forward.score, zrange)):
            x = x.level[i].forward

    assert x != None
    if not zslValueGteMin(x.score, zrange):
        return None
    return x

def zslDeleteRangeByScore(zsl: zskiplist, zrange: zrangespec, d: rDict) -> int:
    def cond(n: zskiplistNode, r: zrangespec):
        return n and (r.minex and (n.score <= r.min) or (n.score < r.min))

    removed = 0
    update: List[Opt[zskiplistNode]] = [None for _ in range(ZSKIPLIST_MAXLEVEL)]

    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while cond(x.level[i].forward, zrange):
            x = x.level[i].forward
        update[i] = x

    x = x.level[0].forward
    while x and (zrange.maxex and x.score < zrange.max or x.score <= zrange.max):
        tmp = x.level[0].forward
        zslDeleteNode(zsl, x, update)
        dictDelete(d, x.obj)
        removed += 1
        x = tmp
    return removed

def zslDeleteRangeByRank(zsl: zskiplist, start: int, end: int, d: rDict) -> int:
    removed = 0
    traversed = 0
    update: List[Opt[zskiplistNode]] = [None for _ in range(ZSKIPLIST_MAXLEVEL)]

    x = zsl.header
    for i in range(zsl.level-1, -1, -1):
        while (x.level[i].forward and (traversed + x.level[i].span < start)):
            traversed += x.level[i].span
            x = x.level[i].forward
        update[i] = x

    traversed += 1
    x = x.level[0].forward
    while (x and traversed <= end):
        tmp = x.level[0].forward
        zslDeleteNode(zsl, x, update)
        dictDelete(d, x.obj)
        zslFreeNode(x)
        removed += 1
        traversed += 1
        x = tmp
    return removed
