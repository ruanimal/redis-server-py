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
        self.next: Opt[listNode] = None
        self.direction: int = 0

class rList:
    def __init__(self):
        self.head: Opt[listNode] = None
        self.tail: Opt[listNode] = None
        self.dup: Callable = None
        self.free: Callable = None
        self.match: Callable = None
        self.len = 0


def listLength(l: rList) -> int:
    return l.len

def listFirst(l: rList) -> Opt[listNode]:
    return l.head

def listLast(l: rList) -> Opt[listNode]:
    return l.tail

def listNodeValue(l: listNode):
    return l.value

def listNextNode(l: listNode) -> Opt[listNode]:
    return l.next

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
    del rList
    # current = l.head
    # length = l.len
    # while length:
    #     length -= 1
    #     next_ = current.next
    #     if l.free:
    #         l.free(current.value)
    #     zfree(current)
    #     current = next_
    # zfree(l)

def listAddNodeHead(l: rList, value) -> rList:
    """把value插入到rList.head之前"""

    node = listNode()
    node.value = value
    if l.len == 0:
        l.head = l.tail = node
        node.prev = node.next = None
    else:
        assert l.head
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
        assert l.tail
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

def listNext(it: listIter) -> Opt[listNode]:
    current = it.next
    if current:
        if it.direction == AL_START_HEAD:
            it.next = current.next
        else:
            it.next = current.prev
    return current

def listDup(orig: rList) -> Opt[rList]:
    copy = listCreate()
    copy.dup = orig.dup
    copy.free = orig.free
    copy.match = orig.match

    it = listGetIterator(orig, AL_START_HEAD)
    while True:
        node = listNext(it)
        if node is None:
            break
        if copy.dup:
            value = copy.dup(node.value)
            if value is None:
                listRelease(copy)
                listReleaseIterator(it)
                return None
        else:
            value = node.value
        listAddNodeTail(copy, value)
        # NOTE 获取内存失败时判断, python 不需要
        # if (listAddNodeTail(copy, value) == NULL) {
        #     listRelease(copy);
        #     listReleaseIterator(iter);
        #     return NULL;
        # }
    listReleaseIterator(it)
    return copy

def listSearchKey(l: rList, key) -> Opt[listNode]:
    it = listGetIterator(l, AL_START_HEAD)
    while True:
        node = listNext(it)
        if node is None:
            break
        if l.match and l.match(node.value, key):
            listReleaseIterator(it)
            return node
        else:
            if key == node.value:
                listReleaseIterator(it)
                return node
    listReleaseIterator(it)
    return None

def listIndex(l: rList, index: int) -> Opt[listNode]:
    if index < 0:
        index = (-index) - 1
        n = l.tail
        while n and index:
            index -= 1
            n = n.prev
    else:
        n = l.head
        while n and index:
            index -= 1
            n = n.next
    return n

def listRotate(l: rList):
    tail = l.tail

    assert tail
    if listLength(l) <= 1:
        return

    l.tail = tail.prev
    assert l.tail
    l.tail.next = None

    assert l.head
    l.head.prev = tail
    tail.prev = None

    tail.next = l.head
    l.head = tail
