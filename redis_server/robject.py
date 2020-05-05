def decrRefCount(o) -> None:
    assert o.refcount > 0
    if o.refcount == 1:
        # TODO: check need job or not
        pass
    else:
        o.refcount -= 1
