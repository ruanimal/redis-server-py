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
