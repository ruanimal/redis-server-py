from typing import List, Callable, Optional as Opt, Tuple, BinaryIO, Dict
from dataclasses import dataclass

# __all__ = [
# ]

@dataclass
class redisCommand(object):
    # 命令名字
    name: str = ''
    # 实现函数
    proc: Callable = None   # type: ignore
    # 参数个数
    arity: int = 0
    # 字符串表示的 FLAG
    sflags: str = ''       # /* Flags as string representation, one char per flag. */
    # 实际 FLAG
    flags: int = 0      # /* The actual flags, obtained from the 'sflags' field. */
    # 从命令中判断命令的键参数。在 Redis 集群转向时使用。
    getkeys_proc: Opt[Callable] = None
    # 指定哪些参数是 key
    firstkey: int = 0   # /* The first argument that's a key (0 = no keys) */
    lastkey: int = 0    # /* The last argument that's a key */
    keystep: int = 0    # /* The step between first and last key */
    # 统计信息
    # microseconds 记录了命令执行耗费的总毫微秒数
    # calls 是命令被执行的总次数
    microseconds: int = 0
    calls: int = 0


def authCommand():
    pass

def execCommand():
    pass

def discardCommand():
    pass

def multiCommand():
    pass

def watchCommand():
    pass

def getCommand():
    pass

def setCommand():
    pass

redisCommandTable = [
    redisCommand("get", getCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    redisCommand("set", setCommand, -3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("setnx", setnxCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("setex", setexCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("psetex", psetexCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("append", appendCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("strlen", strlenCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("del", delCommand, -2, "w", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("exists", existsCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("setbit", setbitCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("getbit", getbitCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("setrange", setrangeCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("getrange", getrangeCommand, 4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("substr", getrangeCommand, 4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("incr", incrCommand, 2, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("decr", decrCommand, 2, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("mget", mgetCommand, -2, "r", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("rpush", rpushCommand, -3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lpush", lpushCommand, -3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("rpushx", rpushxCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lpushx", lpushxCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("linsert", linsertCommand, 5, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("rpop", rpopCommand, 2, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lpop", lpopCommand, 2, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("brpop", brpopCommand, -3, "ws", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("brpoplpush", brpoplpushCommand, 4, "wms", 0, None, 1, 2, 1, 0, 0),
    # redisCommand("blpop", blpopCommand, -3, "ws", 0, None, 1, -2, 1, 0, 0),
    # redisCommand("llen", llenCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lindex", lindexCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lset", lsetCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lrange", lrangeCommand, 4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("ltrim", ltrimCommand, 4, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("lrem", lremCommand, 4, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("rpoplpush", rpoplpushCommand, 3, "wm", 0, None, 1, 2, 1, 0, 0),
    # redisCommand("sadd", saddCommand, -3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("srem", sremCommand, -3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("smove", smoveCommand, 4, "w", 0, None, 1, 2, 1, 0, 0),
    # redisCommand("sismember", sismemberCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("scard", scardCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("spop", spopCommand, 2, "wRs", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("srandmember", srandmemberCommand, -2, "rR", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("sinter", sinterCommand, -2, "rS", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("sinterstore", sinterstoreCommand, -3, "wm", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("sunion", sunionCommand, -2, "rS", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("sunionstore", sunionstoreCommand, -3, "wm", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("sdiff", sdiffCommand, -2, "rS", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("sdiffstore", sdiffstoreCommand, -3, "wm", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("smembers", sinterCommand, 2, "rS", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("sscan", sscanCommand, -3, "rR", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zadd", zaddCommand, -4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zincrby", zincrbyCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrem", zremCommand, -3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zremrangebyscore", zremrangebyscoreCommand, 4, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zremrangebyrank", zremrangebyrankCommand, 4, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zremrangebylex", zremrangebylexCommand, 4, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zunionstore", zunionstoreCommand, -4, "wm", 0, zunionInterGetKeys, 0, 0, 0, 0, 0),
    # redisCommand("zinterstore", zinterstoreCommand, -4, "wm", 0, zunionInterGetKeys, 0, 0, 0, 0, 0),
    # redisCommand("zrange", zrangeCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrangebyscore", zrangebyscoreCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrevrangebyscore", zrevrangebyscoreCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrangebylex", zrangebylexCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrevrangebylex", zrevrangebylexCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zcount", zcountCommand, 4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zlexcount", zlexcountCommand, 4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrevrange", zrevrangeCommand, -4, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zcard", zcardCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zscore", zscoreCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrank", zrankCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zrevrank", zrevrankCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("zscan", zscanCommand, -3, "rR", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hset", hsetCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hsetnx", hsetnxCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hget", hgetCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hmset", hmsetCommand, -4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hmget", hmgetCommand, -3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hincrby", hincrbyCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hincrbyfloat", hincrbyfloatCommand, 4, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hdel", hdelCommand, -3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hlen", hlenCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hkeys", hkeysCommand, 2, "rS", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hvals", hvalsCommand, 2, "rS", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hgetall", hgetallCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hexists", hexistsCommand, 3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("hscan", hscanCommand, -3, "rR", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("incrby", incrbyCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("decrby", decrbyCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("incrbyfloat", incrbyfloatCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("getset", getsetCommand, 3, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("mset", msetCommand, -3, "wm", 0, None, 1, -1, 2, 0, 0),
    # redisCommand("msetnx", msetnxCommand, -3, "wm", 0, None, 1, -1, 2, 0, 0),
    # redisCommand("randomkey", randomkeyCommand, 1, "rR", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("select", selectCommand, 2, "rl", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("move", moveCommand, 3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("rename", renameCommand, 3, "w", 0, None, 1, 2, 1, 0, 0),
    # redisCommand("renamenx", renamenxCommand, 3, "w", 0, None, 1, 2, 1, 0, 0),
    # redisCommand("expire", expireCommand, 3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("expireat", expireatCommand, 3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("pexpire", pexpireCommand, 3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("pexpireat", pexpireatCommand, 3, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("keys", keysCommand, 2, "rS", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("scan", scanCommand, -2, "rR", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("dbsize", dbsizeCommand, 1, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("auth", authCommand, 2, "rslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("ping", pingCommand, 1, "rt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("echo", echoCommand, 2, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("save", saveCommand, 1, "ars", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("bgsave", bgsaveCommand, 1, "ar", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("bgrewriteaof", bgrewriteaofCommand, 1, "ar", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("shutdown", shutdownCommand, -1, "arlt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("lastsave", lastsaveCommand, 1, "rR", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("type", typeCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("multi", multiCommand, 1, "rs", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("exec", execCommand, 1, "sM", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("discard", discardCommand, 1, "rs", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("sync", syncCommand, 1, "ars", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("psync", syncCommand, 3, "ars", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("replconf", replconfCommand, -1, "arslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("flushdb", flushdbCommand, 1, "w", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("flushall", flushallCommand, 1, "w", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("sort", sortCommand, -2, "wm", 0, sortGetKeys, 1, 1, 1, 0, 0),
    # redisCommand("info", infoCommand, -1, "rlt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("monitor", monitorCommand, 1, "ars", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("ttl", ttlCommand, 2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("pttl", pttlCommand, 2, "r", 0, None, 1, 1, 1, 0, 0), Ï
    # redisCommand("persist", persistCommand, 2, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("slaveof", slaveofCommand, 3, "ast", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("debug", debugCommand, -2, "as", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("config", configCommand, -2, "art", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("subscribe", subscribeCommand, -2, "rpslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("unsubscribe", unsubscribeCommand, -1, "rpslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("psubscribe", psubscribeCommand, -2, "rpslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("punsubscribe", punsubscribeCommand, -1, "rpslt", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("publish", publishCommand, 3, "pltr", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("pubsub", pubsubCommand, -2, "pltrR", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("watch", watchCommand, -2, "rs", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("unwatch", unwatchCommand, 1, "rs", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("cluster", clusterCommand, -2, "ar", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("restore", restoreCommand, -4, "awm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("restore-asking", restoreCommand, -4, "awmk", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("migrate", migrateCommand, -6, "aw", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("asking", askingCommand, 1, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("readonly", readonlyCommand, 1, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("readwrite", readwriteCommand, 1, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("dump", dumpCommand, 2, "ar", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("object", objectCommand, -2, "r", 0, None, 2, 2, 2, 0, 0),
    # redisCommand("client", clientCommand, -2, "ar", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("eval", evalCommand, -3, "s", 0, evalGetKeys, 0, 0, 0, 0, 0),
    # redisCommand("evalsha", evalShaCommand, -3, "s", 0, evalGetKeys, 0, 0, 0, 0, 0),
    # redisCommand("slowlog", slowlogCommand, -2, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("script", scriptCommand, -2, "ras", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("time", timeCommand, 1, "rR", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("bitop", bitopCommand, -4, "wm", 0, None, 2, -1, 1, 0, 0),
    # redisCommand("bitcount", bitcountCommand, -2, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("bitpos", bitposCommand, -3, "r", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("wait", waitCommand, 3, "rs", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("pfselftest", pfselftestCommand, 1, "r", 0, None, 0, 0, 0, 0, 0),
    # redisCommand("pfadd", pfaddCommand, -2, "wm", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("pfcount", pfcountCommand, -2, "w", 0, None, 1, 1, 1, 0, 0),
    # redisCommand("pfmerge", pfmergeCommand, -2, "wm", 0, None, 1, -1, 1, 0, 0),
    # redisCommand("pfdebug", pfdebugCommand, -3, "w", 0, None, 0, 0, 0, 0, 0),
]
