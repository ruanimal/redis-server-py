import typing

if typing.TYPE_CHECKING:
    from .redis import RedisClient


def initClientMultiState(c: 'RedisClient'):
    # // 命令队列
    c.mstate.commands = None
    # // 命令计数
    c.mstate.count = 0
