from redis_server.sds import strlen, sdstrim, sdsnew, sdsrange

def test_strlen():
    assert strlen(b'123\0\0') == 3
    assert strlen(b'12\x00123313213') == 2
    assert strlen(b'') == 0
    assert strlen(b'\x00') == 0


def test_sdstrim():
    tmp = b"AA...AA.a.aa.aHelloWorld     :::"
    s = sdstrim(sdsnew(tmp), b"Aa. :")
    assert s.buf.tobytes() == b'HelloWorld\x00a.aHelloWorld     :::\x00'
    assert s.len == len(b'HelloWorld')
    assert s.free == len(tmp) - len(b'HelloWorld')

def test_sdsrange():
    s = sdsnew(b"Hello World")
    sdsrange(s, 1, -1)
    assert s.buf.tobytes() == b'ello World\x00\x00'
    assert s.len == 10
    assert s.free == 1
