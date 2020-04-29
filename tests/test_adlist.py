from redis_server.adlist import *
from typing import Iterable

def rList2list(l: rList) -> list:
    res = []
    res2 = []
    node = l.head
    while node:
        res.append(node.value)
        node = node.next

    node = l.tail
    while node:
        res2.append(node.value)
        node = node.prev
    assert len(res) == l.len
    assert res == res2[::-1]
    return res

def list2rList(l: Iterable) -> rList:
    res = listCreate()
    for i in l:
        listAddNodeTail(res, i)
    return res

def test_listAddNodeHead():
    l = listCreate()
    listAddNodeHead(l, 42)
    assert l.head.value == 42
    assert l.head is l.tail

    listAddNodeHead(l, 43)
    assert l.head.value == 43
    assert l.head.next.value == 42

def test_listAddNodeTail():
    l = listCreate()
    listAddNodeTail(l, 42)
    assert l.head.value == 42
    assert l.head is l.tail

    listAddNodeTail(l, 43)
    assert l.tail.value == 43
    assert l.tail.prev.value == 42

def test_listInsertNode():
    l = listCreate()
    for i in range(10):
        listAddNodeTail(l, i)
    assert rList2list(l) == list(range(10))

def test_listDelNode():
    l = list2rList(range(10))
    node = l.head.next.next  # value == 2
    listDelNode(l, node)
    print(rList2list(l))
    assert rList2list(l) == [0, 1] + list(range(3, 10))

def test_listGetIterator():
    l = list2rList(range(10))
    it = listGetIterator(l, AL_START_HEAD)
    assert it.next == l.head
    assert it.direction == AL_START_HEAD
    it = listGetIterator(l, AL_START_TAIL)
    assert it.next == l.tail
    assert it.direction == AL_START_TAIL

def test_listNext():
    l = list2rList(range(10))
    it = listGetIterator(l, AL_START_HEAD)
    node = listNext(it)
    assert node is l.head

def test_listRewind():
    l = list2rList(range(10))
    it = listGetIterator(l, AL_START_HEAD)
    listNext(it)
    listNext(it)
    assert it.next is l.head.next.next
    listRewind(l, it)
    assert it.next == l.head
    assert it.direction == AL_START_HEAD
    listRewindTail(l, it)
    assert it.next == l.tail
    assert it.direction == AL_START_TAIL

def test_listDup():
    l1 = list2rList(range(10))
    l2 = listDup(l1)

    it1 = listGetIterator(l1, AL_START_HEAD)
    it2 = listGetIterator(l2, AL_START_HEAD)

    n1 = listNext(it1)
    n2 = listNext(it2)
    while n1 and n2:
        assert n1 is not n2
        print(n1.value, n2.value)
        assert n1.value == n2.value
        n1 = listNext(it1)
        n2 = listNext(it2)

def test_listSearchKey():
    l = list2rList(range(10))
    target = l.head.next.next  # value = 2
    t = listSearchKey(l, 2)
    assert target is t
    assert target.value == 2
    t = listSearchKey(l, 11)
    assert t is None

def test_listIndex():
    l = list2rList(range(10))
    target = l.head.next.next  # value = 2
    t = listIndex(l, 2)
    assert target is t
    assert target.value == 2
    t = listIndex(l, 11)
    assert t is None

def test_listRotate():
    l = list2rList(range(10))
    listRotate(l)
    assert rList2list(l) == [9] + list(range(0, 9))
