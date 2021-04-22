import locale
from logging import NOTSET
import random
from sys import argv
import time
import logging
import os
import uuid
import socket
import sys
import platform
import argparse
from typing import List, Callable, Optional as Opt, Tuple, BinaryIO, Dict
from dataclasses import dataclass
from io import BufferedWriter
from collections import OrderedDict
from itertools import chain

from .csix import timeval, int2cstr, zfree
from .ae import (
    AE_WRITABLE, aeDeleteFileEvent, aeEventLoop, aeSetBeforeSleepProc, aeMain, aeDeleteEventLoop, aeCreateEventLoop,
    aeCreateTimeEvent, aeCreateFileEvent, AE_ERR, AE_READABLE,
)
from .anet import anetTcp6Server, anetTcpServer, anetNonBlock, anetUnixServer, anetEnableTcpNoDelay, anetKeepAlive
from .config import ServerConfig as Conf
from .config import *
from .adlist import (
    listDelNode, listRelease, listSearchKey, rList, listCreate, listSetFreeMethod, listSetDupMethod, listSetMatchMethod,
    listLength,
)
from .rdict import *
from .sds import sds, sdsempty, sdsfree, sdsnew
from .robject import *
from .db import RedisDB, dbDictType, keyptrDictType, keylistDictType, setDictType, evictionPoolAlloc
from .pubsub import freePubsubPattern, listMatchPubsubPattern
from .aof import aofRewriteBufferReset
from .networking import (
    acceptTcpHandler, acceptUnixHandler, freeClientArgv, readQueryFromClient, dupClientReplyValue,
    listMatchObjects,
)
from .multi import initClientMultiState
from .util import Singleton, ll2string, get_server
from .commands import *

__version__ = '0.0.1'

logger = logging.getLogger(__name__)

class multiCmd:
    def __init__(self):
        self.argv: List[redisObject] = []
        self.cmd: redisCommand = None

    @property
    def argc(self):
        return len(self.argv)

class multiState:
    def __init__(self):
        self.commands: List[multiCmd] = []
        self.count: int = 0
        self.minreplicas: int = 0
        self.minreplicas_timeout: int = 0

class blockingState:
    def __init__(self):
        self.timeout: int = 0
        self.keys: rDict = None
        self.target: redisObject = None
        # // 等待 ACK 的复制节点数量
        self.numreplicas: int = 0
        # // 复制偏移量
        self.reploffset: int = 0

class clientBufferLimitsConfig:
    def __init__(self):
        # 硬限制
        self.hard_limit_bytes: int = 0
        # 软限制
        self.soft_limit_bytes: int = 0
        # 软限制时限
        self.soft_limit_seconds: int = 0

@dataclass
class redisOp:
    argv: List[robj] = None
    dbid: int = 0
    target: int = 0

    @property
    def argc(self):
        return len(self.argv)

@dataclass
class redisOpArray:
    ops: redisOp = redisOp()
    numops: int = 0

@dataclass
class saveparam:
    # 多少秒之内
    seconds: int = 0
    # 发生多少次修改
    changes: int = 0

class RedisServer(Singleton):
    def __init__(self):
        self.configfile:str = ''  # 配置文件的绝对路径
        self.hz:int = 0      # serverCron() 每秒调用的次数
        self.db: List[RedisDB] = []
        self.commands: dict = {}   # 命令表（受到 rename 配置选项的作用）
        self.orig_commands: dict = {}   # 命令表（无 rename 配置选项的作用）
        self.el: aeEventLoop = None   # 事件状态
        self.lruclock: int = 0   # /* Clock for LRU eviction */
        # 关闭服务器的标识
        self.shutdown_asap: int = 0      # /* SHUTDOWN needed ASAP */
        # 在执行 serverCron() 时进行渐进式 rehash
        self.activerehashing: int =0     # /* Incremental rehash in serverCron() */
        self.requirepass: str = ''        # /* Pass for AUTH command, or NULL */
        self.pidfile: str = ''            # /* PID file path */
        self.arch_bits: int = 0            # /* 32 or 64 depending on sizeof(long) */
        # serverCron() 函数的运行次数计数器
        self.cronloops: int = 0            # /* Number of times the cron function run */
        # 本服务器的 RUN ID
        self.runid: str = ''    # /* ID always different at every exec. */
        # 服务器是否运行在 SENTINEL 模式
        self.sentinel_mode: int = 0
        # /* Networking */
        # TCP 监听端口
        self.port: int = 0                       # /* TCP listening port */
        self.tcp_backlog: int = 0                # /* TCP listen() backlog */
        # 地址
        self.bindaddr: List[str] = []     # /* Addresses we should bind to */
        # 地址数量
        # self.bindaddr_count: int = 0             # /* Number of addresses in server.bindaddr[] */
        # UNIX 套接字
        self.unixsocket: str = ''               # /* UNIX socket path */
        self.unixsocketperm: int = 0          # /* UNIX socket permission */
        # 描述符
        self.ipfd: List[socket.socket] = []    # /* TCP socket file descriptors */
        # 描述符数量
        # self.ipfd_count: int = 0                 # /* Used slots in ipfd[] */
        # UNIX 套接字文件描述符
        self.sofd: socket.socket = None                       # /* Unix socket file descriptor */
        self.cfd: List[int] = []    # /* Cluster bus listening socket */
        self.cfd_count = 0                  # /* Used slots in cfd[] */
        # 一个链表，保存了所有客户端状态结构
        self.clients: list = []                  # /* List of active clients */
        # 链表，保存了所有待关闭的客户端
        self.clients_to_close: list = []         # /* Clients to close asynchronously */
        # 链表，保存了所有从服务器，以及所有监视器
        self.slaves: list = []
        self.monitors: list = []        # /* List of slaves and MONITORs */
        # 服务器的当前客户端，仅用于崩溃报告
        self.current_client: Opt[RedisClient] = None    # /* Current client, only used on crash report */
        self.clients_paused: int = 0             # /* True if clients are currently paused */
        self.clients_pause_end_time: int = 0    # /* Time when we undo clients_paused */
        # 网络错误
        self.neterr: str = ''    # /* Error buffer for anet.c */
        # MIGRATE 缓存
        self.migrate_cached_sockets: dict = {}   # /* MIGRATE cached sockets */

        self.daemonize: int = 0   # /* True if running as a daemon */
        self.cluster_enabled: int = 0
        self.port: int = 0
        # self.ipfd_count: int = 0
        self.sofd: int = 0
        self.unixsocket: str = ""
        #  RDB / AOF loading information
        #  We are loading data from disk if true
        self.loading: int = 0
        # 正在载入的数据的大小
        self.loading_total_bytes: int = 0
        # 已载入数据的大小
        self.loading_loaded_bytes: int = 0
        # 开始进行载入的时间
        self.loading_start_time: int = 0
        self.loading_process_events_interval_bytes: int = 0
        # 常用命令的快捷连接
        self.delCommand: redisCommand = None
        self.multiCommand: redisCommand = None
        self.lpushCommand: redisCommand = None
        self.lpopCommand: redisCommand = None
        self.rpopCommand: redisCommand = None

        #  Fields used only for stats
        #  服务器启动时间
        #  Server start time
        self.stat_starttime: int = 0
        # 已处理命令的数量
        #  Number of processed commands
        self.stat_numcommands: int = 0
        # 服务器接到的连接请求数量
        #  Number of connections received
        self.stat_numconnections: int = 0
        # 已过期的键数量
        #  Number of expired keys
        self.stat_expiredkeys: int = 0
        # 因为回收内存而被释放的过期键的数量
        #  Number of evicted keys (maxmemory)
        self.stat_evictedkeys: int = 0
        # 成功查找键的次数
        #  Number of successful lookups of keys
        self.stat_keyspace_hits: int = 0
        # 查找键失败的次数
        #  Number of failed lookups of keys
        self.stat_keyspace_misses: int = 0
        # 已使用内存峰值
        #  Max used memory record
        self.stat_peak_memory: int = 0
        # 最后一次执行 fork() 时消耗的时间
        #  Time needed to perform latest fork()
        self.stat_fork_time: int = 0
        # 服务器因为客户端数量过多而拒绝客户端连接的次数
        #  Clients rejected because of maxclients
        self.stat_rejected_conn: int = 0
        # 执行 full sync 的次数
        #  Number of full resyncs with slaves.
        self.stat_sync_full: int = 0
        # PSYNC 成功执行的次数
        #  Number of accepted PSYNC requests.
        self.stat_sync_partial_ok: int = 0
        # PSYNC 执行失败的次数
        #  Number of unaccepted PSYNC requests.
        self.stat_sync_partial_err: int = 0

        #  slowlog
        # 保存了所有慢查询日志的链表
        #  SLOWLOG list of commands
        self.slowlog = None
        # 下一条慢查询日志的 ID
        #  SLOWLOG current entry ID
        self.slowlog_entry_id: int = 0
        # 服务器配置 slowlog-log-slower-than 选项的值
        #  SLOWLOG time limit (to get logged)
        self.slowlog_log_slower_than: int = 0
        # 服务器配置 slowlog-max-len 选项的值
        #  SLOWLOG max number of items logged
        self.slowlog_max_len = 0
        #  RSS sampled in serverCron().
        self.resident_set_size = 0
        #  The following two are used to track instantaneous "load" in terms* of operations per second.
        # 最后一次进行抽样的时间
        #  Timestamp of last sample (in ms)
        self.ops_sec_last_sample_time: int = 0
        # 最后一次抽样时，服务器已执行命令的数量
        #  numcommands in last sample
        self.ops_sec_last_sample_ops: int = 0
        # 抽样结果
        self.ops_sec_samples: List[int] = []
        # 数组索引，用于保存抽样结果，并在需要时回绕到 0
        self.ops_sec_idx = 0

        #  Configuration
        # 日志可见性
        #  Loglevel in redis.conf
        self.verbosity: int = 0
        # 客户端最大空转时间
        #  Client timeout in seconds
        self.maxidletime: int = 0
        # 是否开启 SO_KEEPALIVE 选项
        #  Set SO_KEEPALIVE if non-zero.
        self.tcpkeepalive: int = 0
        #  Can be disabled for testing purposes.
        self.active_expire_enabled: int = 0
        #  Limit for client query buffer length
        self.client_max_querybuf_len: int = 0
        #  Total number of configured DBs
        self.dbnum: int = 0
        #  True if running as a daemon
        self.daemonize: int = 0
        # 客户端输出缓冲区大小限制
        # 数组的元素有 REDIS_CLIENT_LIMIT_NUM_CLASSES 个
        # 每个代表一类客户端：普通、从服务器、pubsub，诸如此类
        self.client_obuf_limits: List[clientBufferLimitsConfig] = \
            [clientBufferLimitsConfig() for _ in range(REDIS_CLIENT_LIMIT_NUM_CLASSES)]

        #  AOF persistence
        # AOF 状态（开启/关闭/可写）
        #  REDIS_AOF_(ON|OFF|WAIT_REWRITE)
        self.aof_state: int = 0
        # 所使用的 fsync 策略（每个写入/每秒/从不）
        #  Kind of fsync() policy
        self.aof_fsync: int = 0
        #  Name of the AOF file
        self.aof_filename: str = 0
        #  Don't fsync if a rewrite is in prog.
        self.aof_no_fsync_on_rewrite: int = 0
        #  Rewrite AOF if % growth is > M and...
        self.aof_rewrite_perc: int = 0
        #  the AOF file is at least N bytes.
        self.aof_rewrite_min_size: int = 0
        # 最后一次执行 BGREWRITEAOF 时， AOF 文件的大小
        #  AOF size on latest startup or rewrite.
        self.aof_rewrite_base_size: int = 0
        # AOF 文件的当前字节大小
        #  AOF current size.
        self.aof_current_size: int = 0
        #  Rewrite once BGSAVE terminates.
        self.aof_rewrite_scheduled: int = 0
        # 负责进行 AOF 重写的子进程 ID
        #  PID if rewriting process
        self.aof_child_pid: int = 0
        # AOF 重写缓存链表，链接着多个缓存块
        #  Hold changes during an AOF rewrite.
        self.aof_rewrite_buf_blocks = None   # NOTE: redis list ?
        # AOF 缓冲区
        #  AOF buffer, written before entering the event loop
        self.aof_buf = None   # TODO(ruan.lj@foxmail.com): sds or bytearry.
        # AOF 文件的描述符
        #  File descriptor of currently selected AOF file
        self.aof_fd: BinaryIO = None
        # AOF 的当前目标数据库
        #  Currently selected DB in AOF
        self.aof_selected_db: int = 0
        # 推迟 write 操作的时间
        #  UNIX time of postponed AOF flush
        self.aof_flush_postponed_start = 0
        # 最后一直执行 fsync 的时间
        #  UNIX time of last fsync()
        self.aof_last_fsync = 0
        #  Time used by last AOF rewrite run.
        self.aof_rewrite_time_last = 0
        # AOF 重写的开始时间
        #  Current AOF rewrite start time.
        self.aof_rewrite_time_start = 0
        # 最后一次执行 BGREWRITEAOF 的结果
        #  REDIS_OK or REDIS_ERR
        self.aof_lastbgrewrite_status: int = 0
        # 记录 AOF 的 write 操作被推迟了多少次
        #  delayed AOF fsync() counter
        self.aof_delayed_fsync: int = 0
        # 指示是否需要每写入一定量的数据，就主动执行一次 fsync()
        #  fsync incrementally while rewriting?
        self.aof_rewrite_incremental_fsync: int = 0
        #  REDIS_OK or REDIS_ERR
        self.aof_last_write_status: int = 0
        #  Valid if aof_last_write_status is ERR
        self.aof_last_write_errno: int = 0

        #  RDB persistence
        # 自从上次 SAVE 执行以来，数据库被修改的次数
        #  Changes to DB from the last save
        self.dirty: int = 0
        # BGSAVE 执行前的数据库被修改次数
        #  Used to restore dirty on failed BGSAVE
        self.dirty_before_bgsave: int = 0
        # 负责执行 BGSAVE 的子进程的 ID
        # 没在执行 BGSAVE 时，设为 -1
        #  PID of RDB saving child
        self.rdb_child_pid: int = 0
        #  Save points array for RDB
        self.saveparams: List[saveparam] = []
        #  Number of saving points
        # self.saveparamslen: int = 0
        #  Name of RDB file
        self.rdb_filename: str = ''
        #  Use compression in RDB?
        self.rdb_compression: int = 0
        #  Use RDB checksum?
        self.rdb_checksum: int = 0
        # 最后一次完成 SAVE 的时间
        #  Unix time of last successful save
        self.lastsave = 0
        # 最后一次尝试执行 BGSAVE 的时间
        #  Unix time of last attempted bgsave
        self.lastbgsave_try = 0
        # 最近一次 BGSAVE 执行耗费的时间
        #  Time used by last RDB save run.
        self.rdb_save_time_last = 0
        # 数据库最近一次开始执行 BGSAVE 的时间
        #  Current RDB save start time.
        self.rdb_save_time_start = 0
        # 最后一次执行 SAVE 的状态
        #  REDIS_OK or REDIS_ERR
        self.lastbgsave_status: int = 0
        #  Don't allow writes if can't BGSAVE
        self.stop_writes_on_bgsave_err: int = 0

        #  Propagation of commands in AOF / replication
        #  Additional command to propagate.
        self.also_propagate: redisOpArray = redisOpArray()

        #  Limits
        self.maxclients: int = 0
        self.maxmemory: int = 0   # /* Max number of memory bytes to use */
        self.maxmemory_policy: int = 0           # /* Policy for key eviction */
        self.maxmemory_samples: int = 0          # /* Pricision of random sampling */

        #  Blocked clients
        #  Number of clients blocked by lists
        self.bpop_blocked_clients: int = 0
        #  list of clients to unblock before next loop
        self.unblocked_clients: list = []
        #  List of readyList structures for BLPOP & co
        self.ready_keys: rList = listCreate()
        #  Sort parameters - qsort_r() is only available under BSD so we* have to take this state global, in order to pass it to sortCompare()
        self.sort_desc: int = 0
        self.sort_alpha: int = 0
        self.sort_bypattern: int = 0
        self.sort_store: int = 0
        #  Zip structure config, see redis.conf for more information
        self.hash_max_ziplist_entries: int = 0
        self.hash_max_ziplist_value: int = 0
        self.list_max_ziplist_entries: int = 0
        self.list_max_ziplist_value: int = 0
        self.set_max_intset_entries: int = 0
        self.zset_max_ziplist_entries: int = 0
        self.zset_max_ziplist_value: int = 0
        self.hll_sparse_max_bytes: int = 0
        #  Unix time sampled every cron cycle.
        self.unixtime: int = 0
        #  Like 'unixtime' but with milliseconds resolution.
        self.mstime: int = 0

        #  Pubsub
        # 字典，键为频道，值为链表
        # 链表中保存了所有订阅某个频道的客户端
        # 新客户端总是被添加到链表的表尾
        #  Map channels to list of subscribed clients
        self.pubsub_channels: rDict = None
        # 这个链表记录了客户端订阅的所有模式的名字
        #  A list of pubsub_patterns
        self.pubsub_patterns: rList = None
        self.notify_keyspace_events: int = 0
        #  Events to propagate via Pub/Sub. This is anxor of REDIS_NOTIFY... flags.
        #  Cluster
        #  Is cluster enabled?  NOTE: not support cluster mode
        self.cluster_enabled: int = 0
        #  Assert & bug reporting
        self.assert_failed: str = ''
        self.assert_file: str = ''
        self.assert_line: int = 0
        #  True if bug report header was already logged.
        self.bug_report_start: int = 0
        #  Software watchdog period in ms. 0 = off
        self.watchdog_period: int = 0
        self.lua_caller = None   # NOTE: not support lua

    @property
    def saveparamslen(self):
        return len(self.saveparams)

    @property
    def bindaddr_count(self):
        return len(self.bindaddr)

    @property
    def ipfd_count(self):
        return len(self.ipfd)


class RedisClient(object):   # pylint: disable=all
    def __init__(self):
        # // 套接字描述符
        self.fd: Opt[socket.socket] = None
        # // 当前正在使用的数据库
        self.db: RedisDB = None
        # // 当前正在使用的数据库的 id （号码）
        self.dictid: int = 0
        # // 客户端的名字
        self.name: redisObject = None
        # // 查询缓冲区
        self.querybuf: sds = sdsempty()
        # // 查询缓冲区长度峰值
        self.querybuf_peak: int = 0   # /* Recent (100ms or more) peak of querybuf size */
        # // 参数数量
        # int argc;
        # // 参数对象数组
        self.argv: List[redisObject] = []
        # // 记录被客户端执行的命令
        self.cmd: Opt[redisCommand] = None
        self.lastcmd: Opt[redisCommand] = None
        # // 请求的类型：内联命令还是多条命令
        self.reqtype: int = 0
        # // 剩余未读取的命令内容数量
        self.multibulklen: int = 0
        # // 命令内容的长度
        self.bulklen: int = 0
        # // 回复链表
        self.reply: rList = None
        # // 回复链表中对象的总大小
        self.reply_bytes: int = 0
        # // 已发送字节，处理 short write 用
        self.sentlen: int = 0
        # // 创建客户端的时间
        self.ctime: int = 0
        # // 客户端最后一次和服务器互动的时间
        self.lastinteraction: int = 0
        # // 客户端的输出缓冲区超过软性限制的时间
        self.obuf_soft_limit_reached_time: int = 0
        # // 客户端状态标志
        self.flags: int = 0
        # // 当 server.requirepass 不为 NULL 时
        # // 代表认证的状态
        # // 0 代表未认证， 1 代表已认证
        self.authenticated: int = 0
        # // 复制状态
        self.replstate: int = 0
        # // 用于保存主服务器传来的 RDB 文件的文件描述符
        self.repldbfd: int = 0
        # // 读取主服务器传来的 RDB 文件的偏移量
        self.repldboff: int = 0
        # // 主服务器传来的 RDB 文件的大小
        self.repldbsize: int = 0
        self.replpreamble: sds = None      # /* replication DB preamble. */
        # // 主服务器的复制偏移量
        self.reploff: int = 0    #      /* replication offset if this is our master */
        # // 从服务器最后一次发送 REPLCONF ACK 时的偏移量
        self.repl_ack_off: int = 0    # /* replication ack offset, if this is a slave */
        # // 从服务器最后一次发送 REPLCONF ACK 的时间
        self.repl_ack_time: int = 0    #/* replication ack time, if this is a slave */
        # // 主服务器的 master run ID
        # // 保存在客户端，用于执行部分重同步
        self.replrunid: str = ''
        # // 从服务器的监听端口号
        self.slave_listening_port: int = 0
        # // 事务状态
        self.mstate: multiState = multiState()
        # // 阻塞类型
        self.btype: int = 0
        # // 阻塞状态
        self.bpop: blockingState = blockingState()
        # // 最后被写入的全局复制偏移量
        self.woff: int = 0
        # // 被监视的键
        self.watched_keys: rList = None
        # // 这个字典记录了客户端所有订阅的频道
        # // 键为频道名字，值为 NULL
        # // 也即是，一个频道的集合
        self.pubsub_channels: rDict = None
        # // 链表，包含多个 pubsubPattern 结构
        # // 记录了所有订阅频道的客户端的信息
        # // 新 pubsubPattern 结构总是被添加到表尾
        self.pubsub_patterns: rList = None
        self.peerid: str = ''
        # /* Response buffer */
        # // 回复偏移量
        self.bufpos: int = 0
        # // 回复缓冲区
        self.buf: bytearray = bytearray(REDIS_REPLY_CHUNK_BYTES)

    @property
    def argc(self) -> int:
        return len(self.argv)


class sharedObjects(Singleton):
    def __init__(self):
        # # 常用回复
        self.crlf: redisObject = createObject(REDIS_STRING, sdsnew("\r\n"))
        self.ok: redisObject = createObject(REDIS_STRING, sdsnew("+OK\r\n"))
        self.err: redisObject = createObject(REDIS_STRING, sdsnew("-ERR\r\n"))
        self.emptybulk: redisObject = createObject(REDIS_STRING, sdsnew("$0\r\n\r\n"))
        self.czero: redisObject = createObject(REDIS_STRING, sdsnew(":0\r\n"))
        self.cone: redisObject = createObject(REDIS_STRING, sdsnew(":1\r\n"))
        self.cnegone: redisObject = createObject(REDIS_STRING, sdsnew(":-1\r\n"))
        self.nullbulk: redisObject = createObject(REDIS_STRING, sdsnew("$-1\r\n"))
        self.nullmultibulk: redisObject = createObject(REDIS_STRING, sdsnew("*-1\r\n"))
        self.emptymultibulk: redisObject = createObject(REDIS_STRING, sdsnew("*0\r\n"))
        self.pong: redisObject = createObject(REDIS_STRING, sdsnew("+PONG\r\n"))
        self.queued: redisObject = createObject(REDIS_STRING, sdsnew("+QUEUED\r\n"))
        self.emptyscan: redisObject = createObject(REDIS_STRING, sdsnew("*2\r\n$1\r\n0\r\n*0\r\n"))
        # 常用错误回复
        self.wrongtypeerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"))
        self.nokeyerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-ERR no such key\r\n"))
        self.syntaxerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-ERR syntax error\r\n"))
        self.sameobjecterr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-ERR source and destination objects are the same\r\n"))
        self.outofrangeerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-ERR index out of range\r\n"))
        self.noscripterr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-NOSCRIPT No matching script. Please use EVAL.\r\n"))
        self.loadingerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-LOADING Redis is loading the dataset in memory\r\n"))
        self.slowscripterr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-BUSY Redis is busy running a script. You can only call SCRIPT KILL or SHUTDOWN NOSAVE.\r\n"))
        self.masterdownerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-MASTERDOWN Link with MASTER is down and slave-serve-stale-data is set to 'no'.\r\n"))
        self.bgsaveerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-MISCONF Redis is configured to save RDB snapshots, but is currently not able to persist on disk. "
            "Commands that may modify the data set are disabled. "
            "Please check Redis logs for details about the error.\r\n"))
        self.roslaveerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-READONLY You can't write against a read only slave.\r\n"))
        self.noautherr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-NOAUTH Authentication required.\r\n"))
        self.oomerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-OOM command not allowed when used memory > 'maxmemory'.\r\n"))
        self.execaborterr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-EXECABORT Transaction discarded because of previous errors.\r\n"))
        self.noreplicaserr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-NOREPLICAS Not enough good slaves to write.\r\n"))
        self.busykeyerr: redisObject = createObject(REDIS_STRING, sdsnew(
            "-BUSYKEY Target key name already exists.\r\n"))

        # 常用字符
        self.space: redisObject = createObject(REDIS_STRING, sdsnew(" "))
        self.colon: redisObject = createObject(REDIS_STRING, sdsnew(":"))
        self.plus: redisObject = createObject(REDIS_STRING, sdsnew("+"))
        # 常用 SELECT 命令
        self.select: List[redisObject] = []
        for i in range(Conf.REDIS_SHARED_SELECT_CMDS):
            dictid_str = bytearray(64)
            dictid_len = ll2string(dictid_str, len(dictid_str), i)
            self.select.append(createObject(REDIS_STRING, sdsnew(
                b"*2\r\n$6\r\nSELECT\r\n$%d\r\n%s\r\n" % (dictid_len, dictid_str))))
        # 常用命令
        self.del_: redisObject = createStringObject("DEL", 3)
        self.rpop: redisObject = createStringObject("RPOP", 4)
        self.lpop: redisObject = createStringObject("LPOP", 4)
        self.lpush: redisObject = createStringObject("LPUSH", 5)
        # 常用整数
        self.integers: List[redisObject] = [createObject(REDIS_STRING, i, REDIS_ENCODING_INT)
                                            for i in range(Conf.REDIS_SHARED_INTEGERS)]
        # 常用长度 bulk 或者 multi bulk 回复
        self.mbulkhdr: List[redisObject] = [createObject(
            REDIS_STRING, sdsnew("*%d\r\n" % i)) for i in range(Conf.REDIS_SHARED_INTEGERS)]
        self.bulkhdr: List[redisObject] = [createObject(
            REDIS_STRING, sdsnew("$%d\r\n" % i)) for i in range(Conf.REDIS_SHARED_INTEGERS)]
        self.minstring: redisObject = createStringObject("minstring", 9)
        self.maxstring: redisObject = createStringObject("maxstring", 9)

def queueMultiCommand(c: 'RedisClient'):
    pass

def lookupCommand(s: sds) -> Opt[redisCommand]:
    server = get_server()
    return server.commands.get(s.text.lower())

def freeMemoryIfNeeded() -> int:
    # TODO(rlj): something to do.
    return REDIS_OK

def call(c: RedisClient, flag: int):
    server = get_server()
    client_old_flags = c.flags
    c.flags &= ~(REDIS_FORCE_AOF|REDIS_FORCE_REPL)
    dirty = server.dirty
    start = timeval.from_datetime().ustime
    c.cmd.proc(c)
    duration = timeval.from_datetime().ustime - start
    dirty = server.dirty - dirty
    c.flags &= ~(REDIS_FORCE_AOF|REDIS_FORCE_REPL)
    c.flags |= client_old_flags & (REDIS_FORCE_AOF|REDIS_FORCE_REPL)
    server.stat_numcommands += 1

def handleClientsBlockedOnLists():
    # TODO(rlj): something to do.
    pass

def processCommand(c: RedisClient) -> int:
    from .networking import addReply, addReplyError
    server = get_server()
    shared = sharedObjects()
    if c.argv[0].ptr.lowereq('quit'):
        addReply(c, shared.ok)
        c.flags |= REDIS_CLOSE_AFTER_REPLY
        return REDIS_ERR

    c.cmd = c.lastcmd = lookupCommand(c.argv[0].ptr)
    if not c.cmd:
        addReplyError(c, "unknown command '%s'" % c.argv[0].ptr.text)
        return REDIS_OK
    elif (c.cmd.arity > 0 and (c.cmd.arity != c.argc)) or (c.argc < -c.cmd.arity):
        addReplyError(c, "wrong number of arguments for '%s' command" % c.cmd.name)
        return REDIS_OK
    if server.requirepass and (not c.authenticated) and c.cmd.proc != authCommand:
        addReply(c, shared.noautherr)
        return REDIS_OK
    if server.maxmemory:
        retval = freeMemoryIfNeeded()
        if (c.cmd.flags & REDIS_CMD_DENYOOM) and retval == REDIS_ERR:
            addReply(c, shared.oomerr)
            return REDIS_OK
    if server.loading and (not (c.cmd.flags & REDIS_CMD_LOADING)):
        addReply(c, shared.loadingerr)
        return REDIS_OK
    if ((c.flags & REDIS_MULTI) and
        c.cmd.proc not in [execCommand, discardCommand, multiCommand, watchCommand]):
        # 在事务上下文中
        queueMultiCommand(c)
        addReply(c, shared.queued)
    else:
        call(c, REDIS_CALL_FULL)
        # 处理那些解除了阻塞的键
        if listLength(server.ready_keys):
            handleClientsBlockedOnLists()
    return REDIS_OK

def selectDb(c: RedisClient, idx: int) -> int:
    server = get_server()
    if idx < 0 or idx > server.dbnum:
        return REDIS_ERR
    c.db = server.db[idx]

def createClient(server: RedisServer, fd: Opt[socket.socket]) -> Opt[RedisClient]:
    c = RedisClient()
    if fd:
        anetNonBlock(fd)
        anetEnableTcpNoDelay(fd)
        if server.tcpkeepalive:
            anetKeepAlive(fd, server.tcpkeepalive)
        if (aeCreateFileEvent(server.el, fd.fileno(), AE_READABLE, readQueryFromClient, c) == AE_ERR):
            fd.close()
            return None

    # 默认数据库
    selectDb(c, 0)
    c.fd = fd
    c.bulklen = -1
    # // 创建时间和最后一次互动时间
    c.ctime = c.lastinteraction = server.unixtime
    # // 复制状态
    c.replstate = REDIS_REPL_NONE
    # // 回复链表
    c.reply = listCreate()
    listSetFreeMethod(c.reply, decrRefCountVoid)
    listSetDupMethod(c.reply, dupClientReplyValue)
    # // 阻塞类型
    c.btype = REDIS_BLOCKED_NONE
    # // 造成客户端阻塞的列表键
    c.bpop.keys = dictCreate(setDictType, None)
    # // 在解除阻塞时将元素推入到 target 指定的键中
    # // BRPOPLPUSH 命令时使用
    # // 进行事务时监视的键
    c.watched_keys = listCreate()
    # // 订阅的频道和模式
    c.pubsub_channels = dictCreate(setDictType, None)
    c.pubsub_patterns = listCreate()
    listSetFreeMethod(c.pubsub_patterns, decrRefCountVoid)
    listSetMatchMethod(c.pubsub_patterns, listMatchObjects)
    # // 如果不是伪客户端，那么添加到服务器的客户端链表中
    if fd:
        server.clients.append(c)
    # // 初始化客户端的事务状态
    initClientMultiState(c)
    return c

def unblockClient(c: RedisClient):
    # TODO(rlj): something to do.
    pass

def freeClientMultiState(c: RedisClient):
    # TODO(rlj): something to do.
    pass

def freeClient(c: RedisClient):
    server = get_server()
    if server.current_client == c:
        server.current_client = None
    c.querybuf = None   # type: ignore
    if c.flags & REDIS_BLOCKED:
        unblockClient(c)
    dictRelease(c.bpop.keys)
    if c.fd:
        aeDeleteFileEvent(server.el, c.fd.fileno(), AE_READABLE)
        aeDeleteFileEvent(server.el, c.fd.fileno(), AE_WRITABLE)
        c.fd.close()
    listRelease(c.reply)
    freeClientArgv(c)

    if c.fd:
        server.clients.remove(c)

    if c.flags & REDIS_UNBLOCKED:
        server.unblocked_clients.remove(c)
    if c.flags & REDIS_CLOSE_ASAP:
        server.clients_to_close.remove(c)
    if c.name:
        decrRefCount(c.name)
    c.argv = []
    c.peerid = ''
    freeClientMultiState(c)
    del c


def populateCommandTable() -> None:
    flags_map = {
        'w': REDIS_CMD_WRITE,
        'r': REDIS_CMD_READONLY,
        'm': REDIS_CMD_DENYOOM,
        'a': REDIS_CMD_ADMIN,
        'p': REDIS_CMD_PUBSUB,
        's': REDIS_CMD_NOSCRIPT,
        'R': REDIS_CMD_RANDOM,
        'S': REDIS_CMD_SORT_FOR_SCRIPT,
        'l': REDIS_CMD_LOADING,
        't': REDIS_CMD_STALE,
        'M': REDIS_CMD_SKIP_MONITOR,
        'k': REDIS_CMD_ASKING,
    }
    for c in redisCommandTable:
        for i in c.sflags:
            c.flags |= flags_map[i]
        server = get_server()
        server.commands[c.name] = c
        server.orig_commands[c.name] = c

def getClientLimitClassByName(name: str) -> int:
    mapping = {
        "normal": REDIS_CLIENT_LIMIT_CLASS_NORMAL,
        "slave": REDIS_CLIENT_LIMIT_CLASS_SLAVE,
        "pubsub": REDIS_CLIENT_LIMIT_CLASS_PUBSUB,
    }
    return mapping.get(name, -1)

def keyspaceEventsStringToFlags(classes: str) -> int:
    flags = 0
    for c in classes:
        if c == 'A':
            flags |= REDIS_NOTIFY_ALL
        elif c == 'g':
            flags |= REDIS_NOTIFY_GENERIC
        elif c == '$':
            flags |= REDIS_NOTIFY_STRING
        elif c == 'l':
            flags |= REDIS_NOTIFY_LIST
        elif c == 's':
            flags |= REDIS_NOTIFY_SET
        elif c == 'h':
            flags |= REDIS_NOTIFY_HASH
        elif c == 'z':
            flags |= REDIS_NOTIFY_ZSET
        elif c == 'x':
            flags |= REDIS_NOTIFY_EXPIRED
        elif c == 'e':
            flags |= REDIS_NOTIFY_EVICTED
        elif c == 'K':
            flags |= REDIS_NOTIFY_KEYSPACE
        elif c == 'E':
            flags |= REDIS_NOTIFY_KEYEVENT
        else:
            return -1
    return flags

def checkForSentinelMode() -> int:
    if 'redis-sentinel' in sys.argv[0]:
        return 1
    if '--sentinel' in sys.argv[1:]:
        return 1
    return 0

def getLRUClock() -> int:
    return int(int(time.time() * 1000) / REDIS_LRU_CLOCK_RESOLUTION) & REDIS_LRU_CLOCK_MAX

def LRUClock() -> int:
    server = RedisServer()
    if not server.loading:
        return getLRUClock()
    return (1000/server.hz <= REDIS_LRU_CLOCK_RESOLUTION) and server.lruclock or getLRUClock()

def initServerConfig(server: RedisServer):
    ## 服务器状态
    # 设置服务器的运行 ID
    server.runid = str(uuid.uuid4())
    # 设置默认配置文件路径
    server.configfile = "";
    # 设置默认服务器频率
    server.hz = Conf.REDIS_DEFAULT_HZ;
    # 设置服务器的运行架构
    server.arch_bits = (platform.architecture()[0] == '64bit') and 64 or 32
    # 设置默认服务器端口号
    server.port = Conf.REDIS_SERVERPORT
    server.tcp_backlog = Conf.REDIS_TCP_BACKLOG
    server.unixsocket = ""
    server.unixsocketperm = Conf.REDIS_DEFAULT_UNIX_SOCKET_PERM
    # server.ipfd_count = 0
    # server.sofd = None
    server.dbnum = Conf.REDIS_DEFAULT_DBNUM
    # server.verbosity = Conf.REDIS_DEFAULT_VERBOSITY
    server.maxidletime = Conf.REDIS_MAXIDLETIME
    server.tcpkeepalive = Conf.REDIS_DEFAULT_TCP_KEEPALIVE
    server.active_expire_enabled = 1
    server.client_max_querybuf_len = REDIS_MAX_QUERYBUF_LEN
    server.saveparams = []
    server.loading = 0
    # server.logfile = "";
    server.daemonize = Conf.REDIS_DEFAULT_DAEMONIZE
    server.aof_state = REDIS_AOF_OFF
    server.aof_fsync = REDIS_DEFAULT_AOF_FSYNC
    server.aof_no_fsync_on_rewrite = Conf.REDIS_DEFAULT_AOF_NO_FSYNC_ON_REWRITE
    server.aof_rewrite_perc = Conf.REDIS_AOF_REWRITE_PERC
    server.aof_rewrite_min_size = Conf.REDIS_AOF_REWRITE_MIN_SIZE
    server.aof_rewrite_base_size = 0
    server.aof_rewrite_scheduled = 0
    server.aof_last_fsync = time.time()
    server.aof_rewrite_time_last = -1
    server.aof_rewrite_time_start = -1
    server.aof_lastbgrewrite_status = REDIS_OK
    server.aof_delayed_fsync = 0
    # server.aof_fd = None
    server.aof_selected_db = -1   # /* Make sure the first time will not match */
    server.aof_flush_postponed_start = 0
    server.aof_rewrite_incremental_fsync = Conf.REDIS_DEFAULT_AOF_REWRITE_INCREMENTAL_FSYNC
    server.pidfile = Conf.REDIS_DEFAULT_PID_FILE
    server.rdb_filename = Conf.REDIS_DEFAULT_RDB_FILENAME
    server.aof_filename = Conf.REDIS_DEFAULT_AOF_FILENAME
    server.requirepass = ""
    server.rdb_compression = Conf.REDIS_DEFAULT_RDB_COMPRESSION
    server.rdb_checksum = Conf.REDIS_DEFAULT_RDB_CHECKSUM
    server.stop_writes_on_bgsave_err = Conf.REDIS_DEFAULT_STOP_WRITES_ON_BGSAVE_ERROR
    server.activerehashing = Conf.REDIS_DEFAULT_ACTIVE_REHASHING
    server.notify_keyspace_events = 0
    server.maxclients = Conf.REDIS_MAX_CLIENTS
    server.bpop_blocked_clients = 0
    # server.maxmemory = Conf.REDIS_DEFAULT_MAXMEMORY
    # server.maxmemory_policy = REDIS_DEFAULT_MAXMEMORY_POLICY
    # server.maxmemory_samples = Conf.REDIS_DEFAULT_MAXMEMORY_SAMPLES
    server.hash_max_ziplist_entries = REDIS_HASH_MAX_ZIPLIST_ENTRIES
    server.hash_max_ziplist_value = REDIS_HASH_MAX_ZIPLIST_VALUE
    server.list_max_ziplist_entries = REDIS_LIST_MAX_ZIPLIST_ENTRIES
    server.list_max_ziplist_value = REDIS_LIST_MAX_ZIPLIST_VALUE
    server.set_max_intset_entries = REDIS_SET_MAX_INTSET_ENTRIES
    server.zset_max_ziplist_entries = REDIS_ZSET_MAX_ZIPLIST_ENTRIES
    server.zset_max_ziplist_value = REDIS_ZSET_MAX_ZIPLIST_VALUE
    server.hll_sparse_max_bytes = REDIS_DEFAULT_HLL_SPARSE_MAX_BYTES
    server.shutdown_asap = 0
    # server.repl_ping_slave_period = Conf.REDIS_REPL_PING_SLAVE_PERIOD
    # server.repl_timeout = Conf.REDIS_REPL_TIMEOUT
    # server.repl_min_slaves_to_write = Conf.REDIS_DEFAULT_MIN_SLAVES_TO_WRITE
    # server.repl_min_slaves_max_lag = Conf.REDIS_DEFAULT_MIN_SLAVES_MAX_LAG
    # server.cluster_enabled = 0
    # server.cluster_node_timeout = Conf.REDIS_CLUSTER_DEFAULT_NODE_TIMEOUT
    # server.cluster_migration_barrier = Conf.REDIS_CLUSTER_DEFAULT_MIGRATION_BARRIER
    # server.cluster_configfile = Conf.REDIS_DEFAULT_CLUSTER_CONFIG_FILE
    # server.lua_caller = NULL
    # server.lua_time_limit = Conf.REDIS_LUA_TIME_LIMIT
    # server.lua_client = NULL
    # server.lua_timedout = 0
    server.migrate_cached_sockets = {}
    server.loading_process_events_interval_bytes = (1024*1024*2)

    # 初始化 LRU 时间
    server.lruclock = getLRUClock()

    # 设置保存条件
    server.saveparams.append(saveparam(60*60,1))
    server.saveparams.append(saveparam(300,100))
    server.saveparams.append(saveparam(60,10000))

    # 初始化命令表
    # 在这里初始化是因为接下来读取 .conf 文件时可能会用到这些命令
    populateCommandTable();
    # server.delCommand = lookupCommandByCString("del");
    # server.multiCommand = lookupCommandByCString("multi");
    # server.lpushCommand = lookupCommandByCString("lpush");
    # server.lpopCommand = lookupCommandByCString("lpop");
    # server.rpopCommand = lookupCommandByCString("rpop");

    # /* Slow log */
    # 初始化慢查询日志
    server.slowlog_log_slower_than = Conf.REDIS_SLOWLOG_LOG_SLOWER_THAN;
    server.slowlog_max_len = Conf.REDIS_SLOWLOG_MAX_LEN;

    # /* Debugging */
    # 初始化调试项
    server.assert_failed = "<no assertion failed>"
    server.assert_file = "<no file>"
    server.assert_line = 0
    server.bug_report_start = 0
    server.watchdog_period = 0


def listenToPort(server: RedisServer) -> int:
    port = server.port
    backlog = server.tcp_backlog
    if not server.bindaddr:
        try:
            s = anetTcp6Server(port, None, backlog)
            anetNonBlock(s)
            server.ipfd.append(s)
        except OSError:
            pass
        s = anetTcpServer(port, None, backlog)
        anetNonBlock(s)
        server.ipfd.append(s)
    for addr in server.bindaddr:
        if ':' in addr:
            s = anetTcp6Server(port, addr, backlog)
        else:
            s = anetTcpServer(port, addr, backlog)
        server.ipfd.append(s)
        anetNonBlock(s)
    return REDIS_OK

def resetServerStats(server: RedisServer):
    server.stat_numcommands = 0
    server.stat_numconnections = 0
    server.stat_expiredkeys = 0
    server.stat_evictedkeys = 0
    server.stat_keyspace_misses = 0
    server.stat_keyspace_hits = 0
    server.stat_fork_time = 0
    server.stat_rejected_conn = 0
    server.stat_sync_full = 0
    server.stat_sync_partial_ok = 0
    server.stat_sync_partial_err = 0
    server.ops_sec_samples = [0 for _ in range(Conf.REDIS_OPS_SEC_SAMPLES)]
    server.ops_sec_idx = 0
    server.ops_sec_last_sample_time = int(time.time() * 1000)
    server.ops_sec_last_sample_ops = 0

def updateCachedTime(server: RedisServer):
    server.unixtime = int(time.time())
    server.mstime = int(time.time() * 1000)

def serverCron(*args):
    pass

def initServer(server: RedisServer):
    # // 设置信号处理函数
    # signal(SIGHUP, SIG_IGN);
    # signal(SIGPIPE, SIG_IGN);
    # setupSignalHandlers();

    logger.info(repr(server))
    server.el = aeCreateEventLoop(server.maxclients+REDIS_EVENTLOOP_FDSET_INCR)
    server.db = [RedisDB() for _ in range(server.dbnum)]
    listenToPort(server)
    if server.unixsocket:
        try:
            os.unlink(server.unixsocket)
        except OSError:
            pass
        server.sofd = anetUnixServer(server.unixsocket, server.unixsocketperm, server.tcp_backlog)
        anetNonBlock(server.sofd)
    assert server.ipfd_count > 0 or server.sofd
    for i in range(server.dbnum):
        server.db[i].dict = dictCreate(dbDictType, None)
        server.db[i].expires = dictCreate(keyptrDictType, None)
        server.db[i].blocking_keys = dictCreate(keylistDictType, None)
        server.db[i].ready_keys = dictCreate(setDictType, None)
        server.db[i].watched_keys = dictCreate(keylistDictType, None)
        server.db[i].eviction_pool = evictionPoolAlloc()
        server.db[i].id = i
        server.db[i].avg_ttl = 0

    server.pubsub_channels = dictCreate(keylistDictType, None)
    server.pubsub_patterns = listCreate()
    server.pubsub_patterns.free = freePubsubPattern
    server.pubsub_patterns.match = listMatchPubsubPattern

    server.cronloops = 0
    server.rdb_child_pid = -1
    server.aof_child_pid = -1
    aofRewriteBufferReset()
    server.aof_buf = sdsempty()
    server.lastsave = int(time.time())
    server.lastbgsave_try = 0
    server.rdb_save_time_last = -1
    server.rdb_save_time_start = -1
    server.dirty = 0
    resetServerStats(server)
    # /* A few stats we don't want to reset: server startup time, and peak mem. */
    server.stat_starttime = int(time.time())
    server.stat_peak_memory = 0
    server.resident_set_size = 0
    server.lastbgsave_status = REDIS_OK
    server.aof_last_write_status = REDIS_OK
    server.aof_last_write_errno = 0
    # server.repl_good_slaves_count = 0
    updateCachedTime(server)

    if aeCreateTimeEvent(server.el, 1, serverCron, None, None) == AE_ERR:
        logger.error("Can't create the serverCron time event.")
        exit(1)
    for fd in server.ipfd:
        if aeCreateFileEvent(server.el, fd.fileno(), AE_READABLE, acceptTcpHandler, None) == AE_ERR:
            logger.error("Unrecoverable error creating server.ipfd file event.")
            exit(1)
    if server.sofd and aeCreateFileEvent(server.el, server.sofd.fileno(), AE_READABLE, acceptUnixHandler, None) == AE_ERR:
        logger.error("Unrecoverable error creating server.sofd file event.")
        exit(1)
    if server.aof_state == REDIS_AOF_ON:
        server.aof_fd = open(server.aof_filename, 'ab')
        os.chmod(server.aof_filename, 0o644)
    # NOTE: 暂时不对内存做限制
    # NOTE: 暂时不支持slowlog
    # NOTE: 暂时不支持bio

def initSentinelConfig():
    pass

def initSentinel():
    pass

def loadServerConfig(server: RedisServer, filename: str, options: dict) -> None:
    config_list = []
    if filename:
        with open(filename) as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                parts = line.rsplit("#")[0].split(maxsplit=1)
                if len(parts) != 2:
                    print('wrong config line {!r}'.format(line))
                    continue
                key, val = parts
                config_list.append((key.lower(), val.strip('"')))

    for key, val in chain(config_list, options.items()):
        if key == 'timeout':
            server.maxidletime = int(val)
        elif key == 'tcp-keepalive':
            server.tcpkeepalive = int(val)
        elif key == 'port':
            server.port = int(val)
        elif key == 'tcp-backlog':
            server.tcp_backlog = int(val)
        elif key == 'bind':
            server.bindaddr = val.split()
            assert len(server.bindaddr) < Conf.REDIS_BINDADDR_MAX
        elif key == 'unixsocket':
            server.unixsocket = val
        elif key == 'unixsocketperm':
            server.unixsocketperm = int(val)
        elif key == 'save':
            if val == '':
                server.saveparams = []
            else:
                args = val.split()
                server.saveparams.append(saveparam(int(args[0], int(args[1]))))
        elif key == 'dir':
            os.chdir(val)
        elif key == 'databases':
            server.dbnum = int(val)
        elif key == 'include':
            loadServerConfig(server, val, {})
        elif key == 'maxclients':
            server.maxclients = int(val)
        elif key == 'rdbcompression':
            server.rdb_compression = int(val)
        elif key == 'rdbchecksum':
            server.rdb_checksum = int(val)
        elif key == 'activerehashing':
            server.activerehashing = int(val)
        elif key == 'daemonize':
            server.daemonize = int(val)
        elif key == 'hz':
            server.hz = int(val)
            server.hz = min(server.hz, Conf.REDIS_MIN_HZ)
            server.hz = max(server.hz, Conf.REDIS_MAX_HZ)
        elif key == 'appendonly':
            server.aof_state = int(val) and REDIS_AOF_ON or REDIS_AOF_OFF
        elif key == 'appendfilename':
            p = os.path.abspath(val)
            os.makedirs(p)
            server.aof_filename = p
        elif key == 'no-appendfsync-on-rewrite':
            server.aof_no_fsync_on_rewrite = int(val)
        elif key == 'appendfsync':
            if val == 'no':
                server.aof_fsync = AOF_FSYNC_NO
            elif val == 'always':
                server.aof_fsync = AOF_FSYNC_ALWAYS
            elif val == 'everysec':
                server.aof_fsync = AOF_FSYNC_EVERYSEC
            else:
                raise ValueError(val)
        elif key == 'auto-aof-rewrite-percentage':
            server.aof_rewrite_perc = int(val)
            assert server.aof_rewrite_perc >= 0
        elif key == 'auto-aof-rewrite-min-size':
            server.aof_rewrite_min_size = int(val)
        elif key == 'aof-rewrite-incremental-fsync':
            server.aof_rewrite_incremental_fsync = int(val)
        elif key == 'requirepass':
            assert len(val) < Conf.REDIS_AUTHPASS_MAX_LEN
            server.requirepass = val
        elif key == 'pidfile':
            server.pidfile = os.path.abspath(val)
        elif key == 'dbfilename':
            server.rdb_filename = val
        elif key == 'hash-max-ziplist-entries':
            server.hash_max_ziplist_entries = int(val)
        elif key == 'hash-max-ziplist-value':
            server.hash_max_ziplist_value = int(val)
        elif key == 'list-max-ziplist-entries':
            server.list_max_ziplist_entries = int(val)
        elif key == 'list-max-ziplist-value':
            server.list_max_ziplist_value = int(val)
        elif key == 'set-max-intset-entries':
            server.set_max_intset_entries = int(val)
        elif key == 'zset-max-ziplist-entries':
            server.zset_max_ziplist_entries = int(val)
        elif key == 'zset-max-ziplist-value':
            server.zset_max_ziplist_value = int(val)
        elif key == 'hll-sparse-max-bytes':
            server.hll_sparse_max_bytes = int(val)
        elif key == 'slowlog-log-slower-than':
            server.slowlog_log_slower_than = int(val)
        elif key == 'slowlog-max-len':
            server.slowlog_max_len = int(val)
        elif key == 'client-output-buffer-limit':
            args = val.split()
            assert len(args) == 4
            c = getClientLimitClassByName(args[0])
            hard, soft, seconds = [int(i) for i in args[1:4]]
            server.client_obuf_limits[c].hard_limit_bytes = hard
            server.client_obuf_limits[c].soft_limit_bytes = soft
            server.client_obuf_limits[c].soft_limit_seconds = seconds
        elif key == 'stop-writes-on-bgsave-error':
            server.stop_writes_on_bgsave_err = int(val)
        elif key == 'notify-keyspace-events':
            server.notify_keyspace_events = keyspaceEventsStringToFlags(val)
            assert server.notify_keyspace_events != -1


def parse_server_args(server: RedisServer) -> Tuple[str, dict]:
    def handle_version(args):
        print('Redis server v={}'.format(__version__))

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', help='show version info and exit', action='store_true')
    parser.add_argument('conf', help='config file path', nargs='?')
    parsed, unknown = parser.parse_known_args()
    options = {}
    for arg in unknown:
        if arg.startswith(("-", "--")):
            tmp = arg.split('=')[0]
            parser.add_argument(tmp)
            options[tmp.strip('-')] = ''
    args = parser.parse_args()

    if args.version:
        handle_version(args)
        exit()

    for key in options:
        options[key] = getattr(args, key, '')
    loadServerConfig(server, args.conf, options)
    if args.conf:
        server.configfile = os.path.abspath(args.conf)
    if not (args.conf or options):
        print("Warning: no config file specified, using the default config")
    return args.conf, options

def daemonize():
    if os.fork() != 0:
        exit()
    os.setsid()
    fd = os.open('/dev/null', os.O_RDWR, 0)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)

def redisAsciiArt(server: RedisServer) -> None:
    art = r'''
                        _._
                   _.-``__ ''-._
              _.-``    `.  `_.  ''-._           Redis {ver} (00000000/0) 64 bit
          .-`` .-```.  ```\/    _.,_ ''-._
         (    '      ,       .-`  | `,    )     Running in {mode} mode
         |`-._`-...-` __...-.``-._|'` _.-'|     Port: {port}
         |    `-._   `._    /     _.-'    |     PID: {pid}
          `-._    `-._  `-./  _.-'    _.-'
         |`-._`-._    `-.__.-'    _.-'_.-'|
         |    `-._`-._        _.-'_.-'    |           http://redis.io
          `-._    `-._`-.__.-'_.-'    _.-'
         |`-._`-._    `-.__.-'    _.-'_.-'|
         |    `-._`-._        _.-'_.-'    |
          `-._    `-._`-.__.-'_.-'    _.-'
              `-._    `-.__.-'    _.-'
                  `-._        _.-'
                      `-.__.-'
    '''
    if server.cluster_enabled:
        mode = "cluster"
    elif server.sentinel_mode:
        mode = "sentinel"
    else:
        mode = "standalone"
    print(art.format(
        ver = __version__,
        mode = mode,
        port = server.port,
        pid = os.getpid(),
    ))

def loadDataFromDisk():
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def beforeSleep(eventLoop: aeEventLoop) -> None:
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def main():
    server = RedisServer()
    locale.setlocale(locale.LC_COLLATE, '')
    random.seed(int(time.time()) ^ os.getpid())
    tv = timeval.from_datetime()
    dictSetHashFunctionSeed(tv.tv_sec ^ tv.tv_usec ^ os.getpid())
    # 检查服务器是否以 Sentinel 模式启动
    server.sentinel_mode = checkForSentinelMode();
    # 初始化服务器
    initServerConfig(server);
    parse_server_args(server)
    # 如果服务器以 Sentinel 模式启动，那么进行 Sentinel 功能相关的初始化
    # 并为要监视的主服务器创建一些相应的数据结构
    # NOTE: not support now
    if (server.sentinel_mode):
        initSentinelConfig()
        initSentinel()
    if (server.daemonize):
        daemonize()

    initServer(server)
    # 为服务器进程设置名字
    # NOTE: not support now
    # redisSetProcTitle(argv[0]);

    redisAsciiArt(server)
    if not server.sentinel_mode:
        logger.warning("Server started, Redis version %s", __version__)
        loadDataFromDisk()
        # NOTE: not support cluster mode.
        if server.ipfd_count > 0:
            logger.info("The server is now ready to accept connections on port %s", server.port)
        if server.sofd:
            logger.info("The server is now ready to accept connections at %s", server.unixsocket)
    else:
        raise NotImplementedError('Not support sentinel_mode yet')
    aeSetBeforeSleepProc(server.el, beforeSleep)
    aeMain(server.el)
    aeDeleteEventLoop(server.el)
    return 0
