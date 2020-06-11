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

REDIS_LRU_BITS = 24
REDIS_LRU_CLOCK_MAX = ((1<<REDIS_LRU_BITS)-1)   # /* Max value of obj->lru */
REDIS_LRU_CLOCK_RESOLUTION = 1000   #  /* LRU clock resolution in ms */

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
