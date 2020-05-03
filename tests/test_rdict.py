from redis_server.rdict import *
from redis_server.rdict import _dictNextPower, _dictExpandIfNeeded

def dict2rDict(d: dict) -> rDict:
    t = dictType()
    t.hashFunction = id
    rd = dictCreate(t, b'')
    for k, v in d.items():
        dictAdd(rd, k, v)
    return rd

def test_dictIntHashFunction():
    h = dictIntHashFunction(0x123456)
    assert h == 4106126350
    h = dictIntHashFunction(0x11123456)
    assert h == 3976877242

def test_dictGenHashFunction():
    h = dictGenHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 12)
    assert h == 1849204924
    h = dictGenHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 7)
    assert h == 3238413135
    h = dictGenHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 2)
    assert h == 1421566646

def test_dictGenCaseHashFunction():
    h = dictGenCaseHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 12)
    assert h == 518116017
    h = dictGenCaseHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 7)
    assert h == 2569441712
    h = dictGenCaseHashFunction(b"fafdfsafafasdfasdfasfdsfdsdfadf", 2)
    assert h == 5863372

def test_dictNextPower():
    assert _dictNextPower(1) == DICT_HT_INITIAL_SIZE
    assert _dictNextPower(5) == 8
    assert _dictNextPower(8) == 8
    assert _dictNextPower(2**64) == 2 ** 63 - 1

def test_dictAddRaw():
    t = dictType()
    t.hashFunction = lambda i: int(i)
    d = dictCreate(t, b'')
    entry = dictAddRaw(d, b'12345')
    assert entry.key == b'12345'
    assert d.ht[0].table[t.hashFunction(b'12345') & 3] is entry

    entry = dictAddRaw(d, b'12345')
    assert entry is None # hash可能相同, 但不支持重复的key

    entry = dictAddRaw(d, b'1234')
    assert d.ht[0].table[t.hashFunction(b'1234') & 2] is entry
