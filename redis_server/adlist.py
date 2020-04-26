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


# list *listInsertNode(list *list, listNode *old_node, void *value, int after);
# void listDelNode(list *list, listNode *node);
# listIter *listGetIterator(list *list, int direction);
# listNode *listNext(listIter *iter);
# void listReleaseIterator(listIter *iter);
# list *listDup(list *orig);
# listNode *listSearchKey(list *list, void *key);
# listNode *listIndex(list *list, long index);
# void listRewind(list *list, listIter *li);
# void listRewindTail(list *list, listIter *li);
# void listRotate(list *list);
