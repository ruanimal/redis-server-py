from redis_server.zskiplist import *
from redis_server.robject import createStringObject

def test_zslInsert():
    zsl = zslCreate()
    a = zslInsert(zsl, 1, createStringObject('abcd', 4))
    rank = zslGetRank(zsl, 1, createStringObject('abcd', 4))
    t = zslGetElementByRank(zsl, rank+1)
    print(t.obj, t.score)
    assert t.obj.ptr == bytearray(b'abcd\x00')
