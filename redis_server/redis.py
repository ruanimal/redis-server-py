import locale
import random
import time
import logging
import os
from typing import List, Callable, Optional as Opt, Tuple
from .csix import timeval
from .ae import aeEventLoop, aeSetBeforeSleepProc, aeMain, aeDeleteEventLoop

__version__ = '0.0.1'

logger = logging.getLogger(__name__)

class RedisServer(object):
    def __init__(self):
        self.configfile:str = ''  # 配置文件的绝对路径
        self.hz:int = 0      # serverCron() 每秒调用的次数
        self.db: List['RedisDB'] = []
        self.commands: dict = {}   # 命令表（受到 rename 配置选项的作用）
        self.orig_commands: dict = {}   # 命令表（无 rename 配置选项的作用）
        self.el: aeEventLoop = None   # 事件状态

        self.daemonize: int = 0   # /* True if running as a daemon */
        self.cluster_enabled: int = 0
        self.sentinel_mode: int = 0
        self.port: int = 0
        self.ipfd_count: int = 0
        self.sofd: int = 0
        self.unixsocket: str = ""

"""        命令表（受到 rename 配置选项的作用）
    dict *commands;             /* Command table */
    // 命令表（无 rename 配置选项的作用）
    dict *orig_commands;        /* Command table before command renaming. */

    // 事件状态
    aeEventLoop *el;

    // 最近一次使用时钟
    unsigned lruclock:REDIS_LRU_BITS; /* Clock for LRU eviction */

    // 关闭服务器的标识
    int shutdown_asap;          /* SHUTDOWN needed ASAP */

    // 在执行 serverCron() 时进行渐进式 rehash
    int activerehashing;        /* Incremental rehash in serverCron() */

    // 是否设置了密码
    char *requirepass;          /* Pass for AUTH command, or NULL */

    // PID 文件
    char *pidfile;              /* PID file path */

    // 架构类型
    int arch_bits;              /* 32 or 64 depending on sizeof(long) */

    // serverCron() 函数的运行次数计数器
    int cronloops;              /* Number of times the cron function run */

    // 本服务器的 RUN ID
    char runid[REDIS_RUN_ID_SIZE+1];  /* ID always different at every exec. */

    // 服务器是否运行在 SENTINEL 模式
    int sentinel_mode;          /* True if this instance is a Sentinel. */


    /* Networking */

    // TCP 监听端口
    int port;                   /* TCP listening port */

    int tcp_backlog;            /* TCP listen() backlog */

    // 地址
    char *bindaddr[REDIS_BINDADDR_MAX]; /* Addresses we should bind to */
    // 地址数量
    int bindaddr_count;         /* Number of addresses in server.bindaddr[] */

    // UNIX 套接字
    char *unixsocket;           /* UNIX socket path */
    mode_t unixsocketperm;      /* UNIX socket permission */

    // 描述符
    int ipfd[REDIS_BINDADDR_MAX]; /* TCP socket file descriptors */
    // 描述符数量
    int ipfd_count;             /* Used slots in ipfd[] */

    // UNIX 套接字文件描述符
    int sofd;                   /* Unix socket file descriptor */

    int cfd[REDIS_BINDADDR_MAX];/* Cluster bus listening socket */
    int cfd_count;              /* Used slots in cfd[] */

    // 一个链表，保存了所有客户端状态结构
    list *clients;              /* List of active clients */
    // 链表，保存了所有待关闭的客户端
    list *clients_to_close;     /* Clients to close asynchronously */

    // 链表，保存了所有从服务器，以及所有监视器
    list *slaves, *monitors;    /* List of slaves and MONITORs */

    // 服务器的当前客户端，仅用于崩溃报告
    redisClient *current_client; /* Current client, only used on crash report */

    int clients_paused;         /* True if clients are currently paused */
    mstime_t clients_pause_end_time; /* Time when we undo clients_paused */

    // 网络错误
    char neterr[ANET_ERR_LEN];   /* Error buffer for anet.c */

    // MIGRATE 缓存
    dict *migrate_cached_sockets;/* MIGRATE cached sockets */


    /* RDB / AOF loading information */

    // 这个值为真时，表示服务器正在进行载入
    int loading;                /* We are loading data from disk if true */

    // 正在载入的数据的大小
    off_t loading_total_bytes;

    // 已载入数据的大小
    off_t loading_loaded_bytes;

    // 开始进行载入的时间
    time_t loading_start_time;
    off_t loading_process_events_interval_bytes;

    /* Fast pointers to often looked up command */
    // 常用命令的快捷连接
    struct redisCommand *delCommand, *multiCommand, *lpushCommand, *lpopCommand,
                        *rpopCommand;


    /* Fields used only for stats */

    // 服务器启动时间
    time_t stat_starttime;          /* Server start time */

    // 已处理命令的数量
    long long stat_numcommands;     /* Number of processed commands */

    // 服务器接到的连接请求数量
    long long stat_numconnections;  /* Number of connections received */

    // 已过期的键数量
    long long stat_expiredkeys;     /* Number of expired keys */

    // 因为回收内存而被释放的过期键的数量
    long long stat_evictedkeys;     /* Number of evicted keys (maxmemory) */

    // 成功查找键的次数
    long long stat_keyspace_hits;   /* Number of successful lookups of keys */

    // 查找键失败的次数
    long long stat_keyspace_misses; /* Number of failed lookups of keys */

    // 已使用内存峰值
    size_t stat_peak_memory;        /* Max used memory record */

    // 最后一次执行 fork() 时消耗的时间
    long long stat_fork_time;       /* Time needed to perform latest fork() */

    // 服务器因为客户端数量过多而拒绝客户端连接的次数
    long long stat_rejected_conn;   /* Clients rejected because of maxclients */

    // 执行 full sync 的次数
    long long stat_sync_full;       /* Number of full resyncs with slaves. */

    // PSYNC 成功执行的次数
    long long stat_sync_partial_ok; /* Number of accepted PSYNC requests. */

    // PSYNC 执行失败的次数
    long long stat_sync_partial_err;/* Number of unaccepted PSYNC requests. */


    /* slowlog */

    // 保存了所有慢查询日志的链表
    list *slowlog;                  /* SLOWLOG list of commands */

    // 下一条慢查询日志的 ID
    long long slowlog_entry_id;     /* SLOWLOG current entry ID */

    // 服务器配置 slowlog-log-slower-than 选项的值
    long long slowlog_log_slower_than; /* SLOWLOG time limit (to get logged) */

    // 服务器配置 slowlog-max-len 选项的值
    unsigned long slowlog_max_len;     /* SLOWLOG max number of items logged */
    size_t resident_set_size;       /* RSS sampled in serverCron(). */
    /* The following two are used to track instantaneous "load" in terms
     * of operations per second. */
    // 最后一次进行抽样的时间
    long long ops_sec_last_sample_time; /* Timestamp of last sample (in ms) */
    // 最后一次抽样时，服务器已执行命令的数量
    long long ops_sec_last_sample_ops;  /* numcommands in last sample */
    // 抽样结果
    long long ops_sec_samples[REDIS_OPS_SEC_SAMPLES];
    // 数组索引，用于保存抽样结果，并在需要时回绕到 0
    int ops_sec_idx;


    /* Configuration */

    // 日志可见性
    int verbosity;                  /* Loglevel in redis.conf */

    // 客户端最大空转时间
    int maxidletime;                /* Client timeout in seconds */

    // 是否开启 SO_KEEPALIVE 选项
    int tcpkeepalive;               /* Set SO_KEEPALIVE if non-zero. */
    int active_expire_enabled;      /* Can be disabled for testing purposes. */
    size_t client_max_querybuf_len; /* Limit for client query buffer length */
    int dbnum;                      /* Total number of configured DBs */
    int daemonize;                  /* True if running as a daemon */
    // 客户端输出缓冲区大小限制
    // 数组的元素有 REDIS_CLIENT_LIMIT_NUM_CLASSES 个
    // 每个代表一类客户端：普通、从服务器、pubsub，诸如此类
    clientBufferLimitsConfig client_obuf_limits[REDIS_CLIENT_LIMIT_NUM_CLASSES];


    /* AOF persistence */

    // AOF 状态（开启/关闭/可写）
    int aof_state;                  /* REDIS_AOF_(ON|OFF|WAIT_REWRITE) */

    // 所使用的 fsync 策略（每个写入/每秒/从不）
    int aof_fsync;                  /* Kind of fsync() policy */
    char *aof_filename;             /* Name of the AOF file */
    int aof_no_fsync_on_rewrite;    /* Don't fsync if a rewrite is in prog. */
    int aof_rewrite_perc;           /* Rewrite AOF if % growth is > M and... */
    off_t aof_rewrite_min_size;     /* the AOF file is at least N bytes. */

    // 最后一次执行 BGREWRITEAOF 时， AOF 文件的大小
    off_t aof_rewrite_base_size;    /* AOF size on latest startup or rewrite. */

    // AOF 文件的当前字节大小
    off_t aof_current_size;         /* AOF current size. */
    int aof_rewrite_scheduled;      /* Rewrite once BGSAVE terminates. */

    // 负责进行 AOF 重写的子进程 ID
    pid_t aof_child_pid;            /* PID if rewriting process */

    // AOF 重写缓存链表，链接着多个缓存块
    list *aof_rewrite_buf_blocks;   /* Hold changes during an AOF rewrite. */

    // AOF 缓冲区
    sds aof_buf;      /* AOF buffer, written before entering the event loop */

    // AOF 文件的描述符
    int aof_fd;       /* File descriptor of currently selected AOF file */

    // AOF 的当前目标数据库
    int aof_selected_db; /* Currently selected DB in AOF */

    // 推迟 write 操作的时间
    time_t aof_flush_postponed_start; /* UNIX time of postponed AOF flush */

    // 最后一直执行 fsync 的时间
    time_t aof_last_fsync;            /* UNIX time of last fsync() */
    time_t aof_rewrite_time_last;   /* Time used by last AOF rewrite run. */

    // AOF 重写的开始时间
    time_t aof_rewrite_time_start;  /* Current AOF rewrite start time. */

    // 最后一次执行 BGREWRITEAOF 的结果
    int aof_lastbgrewrite_status;   /* REDIS_OK or REDIS_ERR */

    // 记录 AOF 的 write 操作被推迟了多少次
    unsigned long aof_delayed_fsync;  /* delayed AOF fsync() counter */

    // 指示是否需要每写入一定量的数据，就主动执行一次 fsync()
    int aof_rewrite_incremental_fsync;/* fsync incrementally while rewriting? */
    int aof_last_write_status;      /* REDIS_OK or REDIS_ERR */
    int aof_last_write_errno;       /* Valid if aof_last_write_status is ERR */
    /* RDB persistence */

    // 自从上次 SAVE 执行以来，数据库被修改的次数
    long long dirty;                /* Changes to DB from the last save */

    // BGSAVE 执行前的数据库被修改次数
    long long dirty_before_bgsave;  /* Used to restore dirty on failed BGSAVE */

    // 负责执行 BGSAVE 的子进程的 ID
    // 没在执行 BGSAVE 时，设为 -1
    pid_t rdb_child_pid;            /* PID of RDB saving child */
    struct saveparam *saveparams;   /* Save points array for RDB */
    int saveparamslen;              /* Number of saving points */
    char *rdb_filename;             /* Name of RDB file */
    int rdb_compression;            /* Use compression in RDB? */
    int rdb_checksum;               /* Use RDB checksum? */

    // 最后一次完成 SAVE 的时间
    time_t lastsave;                /* Unix time of last successful save */

    // 最后一次尝试执行 BGSAVE 的时间
    time_t lastbgsave_try;          /* Unix time of last attempted bgsave */

    // 最近一次 BGSAVE 执行耗费的时间
    time_t rdb_save_time_last;      /* Time used by last RDB save run. */

    // 数据库最近一次开始执行 BGSAVE 的时间
    time_t rdb_save_time_start;     /* Current RDB save start time. */

    // 最后一次执行 SAVE 的状态
    int lastbgsave_status;          /* REDIS_OK or REDIS_ERR */
    int stop_writes_on_bgsave_err;  /* Don't allow writes if can't BGSAVE */


    /* Propagation of commands in AOF / replication */
    redisOpArray also_propagate;    /* Additional command to propagate. */


    /* Logging */
    char *logfile;                  /* Path of log file */
    int syslog_enabled;             /* Is syslog enabled? */
    char *syslog_ident;             /* Syslog ident */
    int syslog_facility;            /* Syslog facility */


    /* Replication (master) */
    int slaveseldb;                 /* Last SELECTed DB in replication output */
    // 全局复制偏移量（一个累计值）
    long long master_repl_offset;   /* Global replication offset */
    // 主服务器发送 PING 的频率
    int repl_ping_slave_period;     /* Master pings the slave every N seconds */

    // backlog 本身
    char *repl_backlog;             /* Replication backlog for partial syncs */
    // backlog 的长度
    long long repl_backlog_size;    /* Backlog circular buffer size */
    // backlog 中数据的长度
    long long repl_backlog_histlen; /* Backlog actual data length */
    // backlog 的当前索引
    long long repl_backlog_idx;     /* Backlog circular buffer current offset */
    // backlog 中可以被还原的第一个字节的偏移量
    long long repl_backlog_off;     /* Replication offset of first byte in the
                                       backlog buffer. */
    // backlog 的过期时间
    time_t repl_backlog_time_limit; /* Time without slaves after the backlog
                                       gets released. */

    // 距离上一次有从服务器的时间
    time_t repl_no_slaves_since;    /* We have no slaves since that time.
                                       Only valid if server.slaves len is 0. */

    // 是否开启最小数量从服务器写入功能
    int repl_min_slaves_to_write;   /* Min number of slaves to write. */
    // 定义最小数量从服务器的最大延迟值
    int repl_min_slaves_max_lag;    /* Max lag of <count> slaves to write. */
    // 延迟良好的从服务器的数量
    int repl_good_slaves_count;     /* Number of slaves with lag <= max_lag. */


    /* Replication (slave) */
    // 主服务器的验证密码
    char *masterauth;               /* AUTH with this password with master */
    // 主服务器的地址
    char *masterhost;               /* Hostname of master */
    // 主服务器的端口
    int masterport;                 /* Port of master */
    // 超时时间
    int repl_timeout;               /* Timeout after N seconds of master idle */
    // 主服务器所对应的客户端
    redisClient *master;     /* Client that is master for this slave */
    // 被缓存的主服务器，PSYNC 时使用
    redisClient *cached_master; /* Cached master to be reused for PSYNC. */
    int repl_syncio_timeout; /* Timeout for synchronous I/O calls */
    // 复制的状态（服务器是从服务器时使用）
    int repl_state;          /* Replication status if the instance is a slave */
    // RDB 文件的大小
    off_t repl_transfer_size; /* Size of RDB to read from master during sync. */
    // 已读 RDB 文件内容的字节数
    off_t repl_transfer_read; /* Amount of RDB read from master during sync. */
    // 最近一次执行 fsync 时的偏移量
    // 用于 sync_file_range 函数
    off_t repl_transfer_last_fsync_off; /* Offset when we fsync-ed last time. */
    // 主服务器的套接字
    int repl_transfer_s;     /* Slave -> Master SYNC socket */
    // 保存 RDB 文件的临时文件的描述符
    int repl_transfer_fd;    /* Slave -> Master SYNC temp file descriptor */
    // 保存 RDB 文件的临时文件名字
    char *repl_transfer_tmpfile; /* Slave-> master SYNC temp file name */
    // 最近一次读入 RDB 内容的时间
    time_t repl_transfer_lastio; /* Unix time of the latest read, for timeout */
    int repl_serve_stale_data; /* Serve stale data when link is down? */
    // 是否只读从服务器？
    int repl_slave_ro;          /* Slave is read only? */
    // 连接断开的时长
    time_t repl_down_since; /* Unix time at which link with master went down */
    // 是否要在 SYNC 之后关闭 NODELAY ？
    int repl_disable_tcp_nodelay;   /* Disable TCP_NODELAY after SYNC? */
    // 从服务器优先级
    int slave_priority;             /* Reported in INFO and used by Sentinel. */
    // 本服务器（从服务器）当前主服务器的 RUN ID
    char repl_master_runid[REDIS_RUN_ID_SIZE+1];  /* Master run id for PSYNC. */
    // 初始化偏移量
    long long repl_master_initial_offset;         /* Master PSYNC offset. */


    /* Replication script cache. */
    // 复制脚本缓存
    // 字典
    dict *repl_scriptcache_dict;        /* SHA1 all slaves are aware of. */
    // FIFO 队列
    list *repl_scriptcache_fifo;        /* First in, first out LRU eviction. */
    // 缓存的大小
    int repl_scriptcache_size;          /* Max number of elements. */

    /* Synchronous replication. */
    list *clients_waiting_acks;         /* Clients waiting in WAIT command. */
    int get_ack_from_slaves;            /* If true we send REPLCONF GETACK. */
    /* Limits */
    int maxclients;                 /* Max number of simultaneous clients */
    unsigned long long maxmemory;   /* Max number of memory bytes to use */
    int maxmemory_policy;           /* Policy for key eviction */
    int maxmemory_samples;          /* Pricision of random sampling */


    /* Blocked clients */
    unsigned int bpop_blocked_clients; /* Number of clients blocked by lists */
    list *unblocked_clients; /* list of clients to unblock before next loop */
    list *ready_keys;        /* List of readyList structures for BLPOP & co */


    /* Sort parameters - qsort_r() is only available under BSD so we
     * have to take this state global, in order to pass it to sortCompare() */
    int sort_desc;
    int sort_alpha;
    int sort_bypattern;
    int sort_store;


    /* Zip structure config, see redis.conf for more information  */
    size_t hash_max_ziplist_entries;
    size_t hash_max_ziplist_value;
    size_t list_max_ziplist_entries;
    size_t list_max_ziplist_value;
    size_t set_max_intset_entries;
    size_t zset_max_ziplist_entries;
    size_t zset_max_ziplist_value;
    size_t hll_sparse_max_bytes;
    time_t unixtime;        /* Unix time sampled every cron cycle. */
    long long mstime;       /* Like 'unixtime' but with milliseconds resolution. */


    /* Pubsub */
    // 字典，键为频道，值为链表
    // 链表中保存了所有订阅某个频道的客户端
    // 新客户端总是被添加到链表的表尾
    dict *pubsub_channels;  /* Map channels to list of subscribed clients */

    // 这个链表记录了客户端订阅的所有模式的名字
    list *pubsub_patterns;  /* A list of pubsub_patterns */

    int notify_keyspace_events; /* Events to propagate via Pub/Sub. This is an
                                   xor of REDIS_NOTIFY... flags. */


    /* Cluster */

    int cluster_enabled;      /* Is cluster enabled? */
    mstime_t cluster_node_timeout; /* Cluster node timeout. */
    char *cluster_configfile; /* Cluster auto-generated config file name. */
    struct clusterState *cluster;  /* State of the cluster */

    int cluster_migration_barrier; /* Cluster replicas migration barrier. */
    /* Scripting */

    // Lua 环境
    lua_State *lua; /* The Lua interpreter. We use just one for all clients */

    // 复制执行 Lua 脚本中的 Redis 命令的伪客户端
    redisClient *lua_client;   /* The "fake client" to query Redis from Lua */

    // 当前正在执行 EVAL 命令的客户端，如果没有就是 NULL
    redisClient *lua_caller;   /* The client running EVAL right now, or NULL */

    // 一个字典，值为 Lua 脚本，键为脚本的 SHA1 校验和
    dict *lua_scripts;         /* A dictionary of SHA1 -> Lua scripts */
    // Lua 脚本的执行时限
    mstime_t lua_time_limit;  /* Script timeout in milliseconds */
    // 脚本开始执行的时间
    mstime_t lua_time_start;  /* Start time of script, milliseconds time */

    // 脚本是否执行过写命令
    int lua_write_dirty;  /* True if a write command was called during the
                             execution of the current script. */

    // 脚本是否执行过带有随机性质的命令
    int lua_random_dirty; /* True if a random command was called during the
                             execution of the current script. */

    // 脚本是否超时
    int lua_timedout;     /* True if we reached the time limit for script
                             execution. */

    // 是否要杀死脚本
    int lua_kill;         /* Kill the script if true. */


    /* Assert & bug reporting */

    char *assert_failed;
    char *assert_file;
    int assert_line;
    int bug_report_start; /* True if bug report header was already logged. */
    int watchdog_period;  /* Software watchdog period in ms. 0 = off */"""

server = RedisServer()

def checkForSentinelMode() -> int:
    import sys
    if 'redis-sentinel' in sys.argv[0]:
        return 1
    if '--sentinel' in sys.argv[1:]:
        return 1
    return 0

def initServerConfig():
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def initServer():
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def initSentinelConfig():
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def initSentinel():
    # TODO(ruan.lj@foxmail.com): something to do.
    pass

def loadServerConfig(filename:str, options: dict) -> None:
    from collections import OrderedDict
    config = OrderedDict()
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
                config[key.lower()] = val.strip('"')
    for key, val in options.items():
        config[key] = val
    print(config)
    # TODO(ruan.lj@foxmail.com): set configs to server.

def parse_server_args() -> Tuple[str, dict]:
    def handle_version(args):
        print('Redis server v={}'.format(__version__))

    import argparse
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
    loadServerConfig(args.conf, options)
    if args.conf:
        server.configfile = os.path.abspath(args.conf)
    if not (args.conf or options):
        print("Warning: no config file specified, using the default config")
    return args.conf, options

def daemonize():
    if (os.fork() != 0):
        exit()
    os.setsid()
    fd = os.open('/dev/null', os.O_RDWR, 0)
    os.dup2(fd, 0)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)

def redisAsciiArt() -> None:
    art = (
        "                _._ \n"
        "           _.-``__ ''-._ \n"
        "      _.-``    `.  `_.  ''-._           Redis {ver} (00000000/0) 64 bit \n"
        "  .-`` .-```.  ```\/    _.,_ ''-._ \n"
        " (    '      ,       .-`  | `,    )     Running in {mode} mode \n"
        " |`-._`-...-` __...-.``-._|'` _.-'|     Port: {port} \n"
        " |    `-._   `._    /     _.-'    |     PID: {pid} \n"
        "  `-._    `-._  `-./  _.-'    _.-' \n"
        " |`-._`-._    `-.__.-'    _.-'_.-'| \n"
        " |    `-._`-._        _.-'_.-'    |           http://redis.io \n"
        "  `-._    `-._`-.__.-'_.-'    _.-' \n"
        " |`-._`-._    `-.__.-'    _.-'_.-'| \n"
        " |    `-._`-._        _.-'_.-'    | \n"
        "  `-._    `-._`-.__.-'_.-'    _.-' \n"
        "      `-._    `-.__.-'    _.-' \n"
        "          `-._        _.-' \n"
        "              `-.__.-' \n"
    )
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
    from .rdict import dictSetHashFunctionSeed

    locale.setlocale(locale.LC_COLLATE, '')
    random.seed(int(time.time()) ^ os.getpid())
    tv = timeval.from_datetime()
    dictSetHashFunctionSeed(tv.tv_sec ^ tv.tv_usec ^ os.getpid())
    # 检查服务器是否以 Sentinel 模式启动
    server.sentinel_mode = checkForSentinelMode();
    # 初始化服务器
    initServerConfig();
    # 如果服务器以 Sentinel 模式启动，那么进行 Sentinel 功能相关的初始化
    # 并为要监视的主服务器创建一些相应的数据结构
    if (server.sentinel_mode):
        initSentinelConfig()
        initSentinel()
    if (server.daemonize):
        daemonize()
    # 为服务器进程设置名字
    # NOTE: not support now
    # redisSetProcTitle(argv[0]);

    redisAsciiArt()
    if not server.sentinel_mode:
        logger.warn("Server started, Redis version %s", __version__)
        loadDataFromDisk()
        # NOTE: not support cluster mode.
        if server.ipfd_count > 0:
            logger.info("The server is now ready to accept connections on port %s", server.port)
        if server.sofd > 0:
            logger.info("The server is now ready to accept connections at %s", server.unixsocket)
    else:
        raise NotImplementedError('Not support sentinel_mode yet')
    aeSetBeforeSleepProc(server.el, beforeSleep)
    aeMain(server.el)
    aeDeleteEventLoop(server.el)
    return 0

if __name__ == '__main__':
    parse_server_args()
    # redisAsciiArt()
