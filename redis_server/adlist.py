# -*- coding:utf-8 -*-

from typing import Any, Union, Callable, Optional as Opt, List
from .csix import *


class listNode:
    def __init__(self):
        self.prev: Opt[ListNode] = None
        self.next: Opt[ListNode] = None
        self.value = None


class listIter:
    def __init__(self):
        self.next: listNode = None
        self.direction: int = 0

class rList:
    def __init__(self):
        self.head: listNode = None
        self.tail: listNode = None
        self.dup: Callable = None
        self.free: Callable = None
        self.match: Callable = None
        self.len = 0


def listLength(l: rList) -> int:
    return l.len

def listFirst(l: rList) -> listNode:
    return l.head

def listLast(l: rList) -> listNode:
    return l.tail

def listNodeValue(l: listNode) -> listNode:
    return l.next

def listNextNode(l: listNode):
    return l.value

def listSetDupMethod(l: rList, m: Callable):
    l.dup = m

def listSetFreeMethod(l: rList, m: Callable):
    l.free = m

def listSetMatchMethod(l: rList, m: Callable):
    l.match = m

# 迭代器进行迭代的方向
## 从表头向表尾进行迭代
AL_START_HEAD = 0
## 从表尾到表头进行迭代
AL_START_TAIL = 1

def listCreate() -> rList:
    return rList()

def listRelease(l: rList):
    current = l.head
    length = l.len
    while length:
        length -= 1
        next_ = current.next
        if l.free:
            l.free(current.value)
        zfree(current)
        current = next_
    zfree(l)

def listAddNodeHead(l: rList, value) -> rList:
    """把value插入到rList.head之前"""

    node = listNode()
    node.value = value
    if l.len == 0:
        l.head = l.tail = node
        node.prev = node.next = None
    else:
        node.prev = None
        node.next = l.head
        l.head.prev = node
        l.head = node
    l.len += 1
    return l

def listAddNodeTail(l: rList, value) -> rList:
    """把value插入到rList.tail之后"""

    node = listNode()
    node.value = value
    if l.len == 0:
        l.head = l.tail = node
        node.prev = node.next = None
    else:
        node.prev = l.tail
        node.next = None
        l.tail.next = node
        l.tail = node
    l.len += 1
    return l

def listInsertNode(l: rList, old_node: listNode, value, after: int) -> rList:
    node = listNode()
    node.value = value
    if after:
        node.prev = old_node
        node.next = old_node.next
        if l.tail == old_node:
            l.tail = node
    else:
        node.next = old_node
        node.prev = old_node.prev
        if l.head == old_node:
            l.head = node

    if node.prev is not None:
        node.prev.next = node
    if node.next is not None:
        node.next.prev = node
    l.len += 1
    return l

def listDelNode(l: rList, node: listNode) -> None:
    if node.prev:
        node.prev.next = node.next
    else:
        l.head = node.next
    if node.next:
        node.next.prev = node.prev
    else:
        l.tail = node.prev
    if l.free:
        l.free(node.value)
    zfree(node)
    l.len -= 1

def listGetIterator(l: rList, direction: int) -> listIter:
    it = listIter()
    if direction == AL_START_HEAD:
        it.next = l.head
    else:
        it.next = l.tail
    it.direction = direction
    return it

def listReleaseIterator(it: listIter) -> None:
    zfree(it)

def listRewind(l: rList, li: listIter) -> None:
    li.next = l.head
    li.direction = AL_START_HEAD

def listRewindTail(l: rList, li: listIter) -> None:
    li.next = l.tail
    li.direction = AL_START_TAIL


# listNode *listNext(listIter *iter);
# void listReleaseIterator(listIter *iter);
# list *listDup(list *orig);
# listNode *listSearchKey(list *list, void *key);
# listNode *listIndex(list *list, long index);
# void listRotate(list *list);
