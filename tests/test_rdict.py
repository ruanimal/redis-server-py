from redis_server.rdict import *

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
