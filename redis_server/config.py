import os
import sys

redis_fstat = os.fstat
redis_stat = os.stat

# /* Test for proc filesystem */
if sys.platform == 'linux':
    HAVE_PROC_STAT = 1
    HAVE_PROC_MAPS = 1
    HAVE_PROC_SMAPS = 1

# /* Test for task_info() */
if sys.platform == 'darwin':
    HAVE_TASKINFO = 1

# /* Test for backtrace() */
if sys.platform in ('darwin', 'linux'):
    HAVE_BACKTRACE = 1

# TODO(ruan.lj@foxmail.com): only support select now.
# # /* Test for polling API */
# if sys.platform == 'linux':
#     HAVE_EPOLL = 1
# if sys.platform == 'darwin' or 'bsd' in sys.platform:
#     HAVE_KQUEUE = 1


# /* Define aof_fsync to fdatasync() in Linux and fsync() for all the rest */
if sys.platform == 'linux':
    aof_fsync = os.fdatasync   # pylint: disable=E1101
else:
    aof_fsync = os.fsync

# /* Define rdb_fsync_range to sync_file_range() on Linux, otherwise we use
#  * the plain fsync() call. */
HAVE_SYNC_FILE_RANGE = 0
rdb_fsync_range = lambda fd, offset, size: os.fsync(fd)

# /* Check if we can use setproctitle().
#  * BSD systems have support for it, we provide an implementation for
#  * Linux and osx. */
# TODO(ruan.lj@foxmail.com): no support SETPROCTITLE .
USE_SETPROCTITLE = 0
INIT_SETPROCTITLE_REPLACEMENT = 0

LITTLE_ENDIAN = 1234	 # /* least-significant byte first (vax, pc) */
BIG_ENDIAN = 4321	 # /* most-significant byte first (IBM, net) */
PDP_ENDIAN = 3412	 # /* LSB first in word, MSW first in long (pdp)*/
BYTE_ORDER = sys.byteorder

###########

REDIS_OK = 0
REDIS_ERR = -1

REDIS_LRU_BITS = 24
REDIS_LRU_CLOCK_MAX = ((1<<REDIS_LRU_BITS)-1)   # /* Max value of obj->lru */
REDIS_LRU_CLOCK_RESOLUTION = 1000   #  /* LRU clock resolution in ms */

#/* Protocol and I/O related defines */
REDIS_MAX_QUERYBUF_LEN = (1024*1024*1024)   # /* 1GB max query buffer. */
#define REDIS_IOBUF_LEN         (1024*16)  /* Generic I/O buffer size */
#define REDIS_REPLY_CHUNK_BYTES (16*1024) /* 16k output buffer */
#define REDIS_INLINE_MAX_SIZE   (1024*64) /* Max size of inline reads */
#define REDIS_MBULK_BIG_ARG     (1024*32)
#define REDIS_LONGSTR_SIZE      21          /* Bytes needed for long -> str */

# /* AOF states */
REDIS_AOF_OFF = 0       # /* AOF is off */
REDIS_AOF_ON = 1        #  /* AOF is on */
REDIS_AOF_WAIT_REWRITE = 2      # /* AOF waits rewrite to start appending */

# /* Append only defines */
AOF_FSYNC_NO = 0
AOF_FSYNC_ALWAYS = 1
AOF_FSYNC_EVERYSEC = 2
REDIS_DEFAULT_AOF_FSYNC = AOF_FSYNC_EVERYSEC

# /* Redis maxmemory strategies */
REDIS_MAXMEMORY_VOLATILE_LRU = 0
REDIS_MAXMEMORY_VOLATILE_TTL = 1
REDIS_MAXMEMORY_VOLATILE_RANDOM = 2
REDIS_MAXMEMORY_ALLKEYS_LRU = 3
REDIS_MAXMEMORY_ALLKEYS_RANDOM = 4
REDIS_MAXMEMORY_NO_EVICTION = 5
REDIS_DEFAULT_MAXMEMORY_POLICY = REDIS_MAXMEMORY_NO_EVICTION

# /* Zip structure related defaults */
REDIS_HASH_MAX_ZIPLIST_ENTRIES = 512
REDIS_HASH_MAX_ZIPLIST_VALUE = 64
REDIS_LIST_MAX_ZIPLIST_ENTRIES = 512
REDIS_LIST_MAX_ZIPLIST_VALUE = 64
REDIS_SET_MAX_INTSET_ENTRIES = 512
REDIS_ZSET_MAX_ZIPLIST_ENTRIES = 128
REDIS_ZSET_MAX_ZIPLIST_VALUE = 64

# /* HyperLogLog defines */
REDIS_DEFAULT_HLL_SPARSE_MAX_BYTES = 3000

# /* Client classes for client limits, currently used only for
#  * the max-client-output-buffer limit implementation. */
REDIS_CLIENT_LIMIT_CLASS_NORMAL = 0
REDIS_CLIENT_LIMIT_CLASS_SLAVE = 1
REDIS_CLIENT_LIMIT_CLASS_PUBSUB = 2
REDIS_CLIENT_LIMIT_NUM_CLASSES = 3

# /* Keyspace changes notification classes. Every class is associated with a
#  * character for configuration purposes. */
REDIS_NOTIFY_KEYSPACE = (1<<0)   # /* K */
REDIS_NOTIFY_KEYEVENT = (1<<1)   # /* E */
REDIS_NOTIFY_GENERIC = (1<<2)    # /* g */
REDIS_NOTIFY_STRING = (1<<3)     # /* $ */
REDIS_NOTIFY_LIST = (1<<4)       # /* l */
REDIS_NOTIFY_SET = (1<<5)        # /* s */
REDIS_NOTIFY_HASH = (1<<6)       # /* h */
REDIS_NOTIFY_ZSET = (1<<7)       # /* z */
REDIS_NOTIFY_EXPIRED = (1<<8)    # /* x */
REDIS_NOTIFY_EVICTED = (1<<9)    # /* e */
REDIS_NOTIFY_ALL = (REDIS_NOTIFY_GENERIC | REDIS_NOTIFY_STRING | REDIS_NOTIFY_LIST | REDIS_NOTIFY_SET | REDIS_NOTIFY_HASH | REDIS_NOTIFY_ZSET | REDIS_NOTIFY_EXPIRED | REDIS_NOTIFY_EVICTED)     # /* A */

# /* Protocol and I/O related defines */
REDIS_MAX_QUERYBUF_LEN =  (1024*1024*1024)  # /* 1GB max query buffer. */
REDIS_IOBUF_LEN =         (1024*16)     # /* Generic I/O buffer size */
REDIS_REPLY_CHUNK_BYTES = (16*1024)     # /* 16k output buffer */
REDIS_INLINE_MAX_SIZE =   (1024*64)     # /* Max size of inline reads */
REDIS_MBULK_BIG_ARG =     (1024*32)
REDIS_LONGSTR_SIZE =      21            # /* Bytes needed for long -> str */

# /* Slave replication state - from the point of view of the slave. */
REDIS_REPL_NONE = 0     # /* No active replication */
REDIS_REPL_CONNECT = 1      # /* Must connect to master */
REDIS_REPL_CONNECTING = 2       # /* Connecting to master */
REDIS_REPL_RECEIVE_PONG = 3     # /* Wait for PING reply */
REDIS_REPL_TRANSFER = 4     # /* Receiving .rdb from master */
REDIS_REPL_CONNECTED = 5    # /* Connected to master */

# /* Client block type (btype field in client structure)
#  * if REDIS_BLOCKED flag is set. */
REDIS_BLOCKED_NONE = 0   # /* Not blocked, no REDIS_BLOCKED flag set. */
REDIS_BLOCKED_LIST = 1   # /* BLPOP & co. */
REDIS_BLOCKED_WAIT = 2   # /* WAIT for synchronous replication. */

# /* Client request types */
REDIS_REQ_INLINE = 1
REDIS_REQ_MULTIBULK = 2

# /* Client flags */
REDIS_SLAVE = (1<<0)    #  /* This client is a slave server */
REDIS_MASTER = (1<<1)   # /* This client is a master server */
REDIS_MONITOR = (1<<2)  #/* This client is a slave monitor, see MONITOR */
REDIS_MULTI = (1<<3)    #  /* This client is in a MULTI context */
REDIS_BLOCKED = (1<<4)  #/* The client is waiting in a blocking operation */
REDIS_DIRTY_CAS = (1<<5)    #/* Watched keys modified. EXEC will fail. */
REDIS_CLOSE_AFTER_REPLY = (1<<6)    #/* Close after writing entire reply. */
REDIS_UNBLOCKED = (1<<7)    #/* This client was unblocked and is stored in server.unblocked_clients */
REDIS_LUA_CLIENT = (1<<8)   #/* This is a non connected client used by Lua */
REDIS_ASKING = (1<<9)   #    /* Client issued the ASKING command */
REDIS_CLOSE_ASAP = (1<<10)     #/* Close this client ASAP */
REDIS_UNIX_SOCKET = (1<<11)     #/* Client connected via Unix domain socket */
REDIS_DIRTY_EXEC = (1<<12)  # /* EXEC will fail for errors while queueing */
REDIS_MASTER_FORCE_REPLY = (1<<13)  # /* Queue replies even if is master */
REDIS_FORCE_AOF = (1<<14)   #  /* Force AOF propagation of current cmd. */
REDIS_FORCE_REPL = (1<<15)  # /* Force replication of current cmd. */
REDIS_PRE_PSYNC = (1<<16)   #  /* Instance don't understand PSYNC. */
REDIS_READONLY = (1<<17)    #   /* Cluster client is in read-only state. */

# /* Log levels */
REDIS_DEBUG = 0
REDIS_VERBOSE = 1
REDIS_NOTICE = 2
REDIS_WARNING = 3
REDIS_LOG_RAW = (1<<10)
REDIS_DEFAULT_VERBOSITY = REDIS_NOTICE

# Slave replication state - from the point of view of the master.
REDIS_REPL_WAIT_BGSAVE_START = 6        # /* We need to produce a new RDB file. */
REDIS_REPL_WAIT_BGSAVE_END = 7      # /* Waiting RDB file creation to finish. */
REDIS_REPL_SEND_BULK = 8        # /* Sending RDB file to slave. */
REDIS_REPL_ONLINE = 9       # /* RDB file transmitted, sending just updates. */

# 命令标志
REDIS_CMD_WRITE = 1         # /* "w" flag */
REDIS_CMD_READONLY = 2          # /* "r" flag */
REDIS_CMD_DENYOOM = 4       # /* "m" flag */
REDIS_CMD_NOT_USED_1 = 8        # /* no longer used flag */
REDIS_CMD_ADMIN = 16        # /* "a" flag */
REDIS_CMD_PUBSUB = 32       # /* "p" flag */
REDIS_CMD_NOSCRIPT =  64        # /* "s" flag */
REDIS_CMD_RANDOM = 128          # /* "R" flag */
REDIS_CMD_SORT_FOR_SCRIPT = 256         # /* "S" flag */
REDIS_CMD_LOADING = 512         # /* "l" flag */
REDIS_CMD_STALE = 1024          # /* "t" flag */
REDIS_CMD_SKIP_MONITOR = 2048       # /* "M" flag */
REDIS_CMD_ASKING = 4096         # /* "k" flag */

# /* Command call flags, see call() function */
REDIS_CALL_NONE = 0
REDIS_CALL_SLOWLOG = 1
REDIS_CALL_STATS = 2
REDIS_CALL_PROPAGATE = 4
REDIS_CALL_FULL = (REDIS_CALL_SLOWLOG | REDIS_CALL_STATS | REDIS_CALL_PROPAGATE)

# /* 默认的服务器配置值 */
class ServerConfig:
    REDIS_DEFAULT_HZ =        10     # /* Time interrupt calls/sec. */
    REDIS_MIN_HZ =            1
    REDIS_MAX_HZ =            500
    REDIS_SERVERPORT =        6379   # /* TCP port */
    REDIS_TCP_BACKLOG =       511    # /* TCP listen backlog */
    REDIS_MAXIDLETIME =       0      # /* default client timeout: infinite */
    REDIS_DEFAULT_DBNUM =     16
    REDIS_CONFIGLINE_MAX =    1024
    REDIS_DBCRON_DBS_PER_CALL = 16
    REDIS_MAX_WRITE_PER_EVENT = (1024*64)
    REDIS_SHARED_SELECT_CMDS = 10
    REDIS_SHARED_INTEGERS = 10000
    REDIS_SHARED_BULKHDR_LEN = 32
    REDIS_MAX_LOGMSG_LEN =    1024  # /* Default maximum length of syslog messages */
    REDIS_AOF_REWRITE_PERC =  100
    REDIS_AOF_REWRITE_MIN_SIZE = (64*1024*1024)
    REDIS_AOF_REWRITE_ITEMS_PER_CMD = 64
    REDIS_SLOWLOG_LOG_SLOWER_THAN = 10000
    REDIS_SLOWLOG_MAX_LEN = 128
    REDIS_MAX_CLIENTS = 10000
    REDIS_AUTHPASS_MAX_LEN = 512
    REDIS_DEFAULT_SLAVE_PRIORITY = 100
    REDIS_REPL_TIMEOUT = 60
    REDIS_REPL_PING_SLAVE_PERIOD = 10
    REDIS_RUN_ID_SIZE = 36     #  NOTE: origin is 40
    REDIS_OPS_SEC_SAMPLES = 16
    REDIS_DEFAULT_REPL_BACKLOG_SIZE = (1024*1024)    # /* 1mb */
    REDIS_DEFAULT_REPL_BACKLOG_TIME_LIMIT = (60*60)  # /* 1 hour */
    REDIS_REPL_BACKLOG_MIN_SIZE = (1024*16)          # /* 16k */
    REDIS_BGSAVE_RETRY_DELAY = 5  # /* Wait a few secs before trying again. */
    REDIS_DEFAULT_PID_FILE = "/var/run/redis.pid"
    REDIS_DEFAULT_SYSLOG_IDENT = "redis"
    REDIS_DEFAULT_CLUSTER_CONFIG_FILE = "nodes.conf"
    REDIS_DEFAULT_DAEMONIZE = 0
    REDIS_DEFAULT_UNIX_SOCKET_PERM = 0
    REDIS_DEFAULT_TCP_KEEPALIVE = 0
    REDIS_DEFAULT_LOGFILE = ""
    REDIS_DEFAULT_SYSLOG_ENABLED = 0
    REDIS_DEFAULT_STOP_WRITES_ON_BGSAVE_ERROR = 1
    REDIS_DEFAULT_RDB_COMPRESSION = 1
    REDIS_DEFAULT_RDB_CHECKSUM = 1
    REDIS_DEFAULT_RDB_FILENAME = "dump.rdb"
    REDIS_DEFAULT_SLAVE_SERVE_STALE_DATA = 1
    REDIS_DEFAULT_SLAVE_READ_ONLY = 1
    REDIS_DEFAULT_REPL_DISABLE_TCP_NODELAY = 0
    REDIS_DEFAULT_MAXMEMORY = 0
    REDIS_DEFAULT_MAXMEMORY_SAMPLES = 5
    REDIS_DEFAULT_AOF_FILENAME = "appendonly.aof"
    REDIS_DEFAULT_AOF_NO_FSYNC_ON_REWRITE = 0
    REDIS_DEFAULT_ACTIVE_REHASHING = 1
    REDIS_DEFAULT_AOF_REWRITE_INCREMENTAL_FSYNC = 1
    REDIS_DEFAULT_MIN_SLAVES_TO_WRITE = 0
    REDIS_DEFAULT_MIN_SLAVES_MAX_LAG = 10
    REDIS_IP_STR_LEN = 46   # INET6_ADDRSTRLEN
    REDIS_PEER_ID_LEN = (REDIS_IP_STR_LEN+32)  # /* Must be enough for ip:port */
    REDIS_BINDADDR_MAX = 16
    REDIS_MIN_RESERVED_FDS = 32

# /* When configuring the Redis eventloop, we setup it so that the total number
#  * of file descriptors we can handle are server.maxclients + RESERVED_FDS + FDSET_INCR
#  * that is our safety margin. */
REDIS_EVENTLOOP_FDSET_INCR = (ServerConfig.REDIS_MIN_RESERVED_FDS+96)
