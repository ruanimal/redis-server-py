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

LITTLE_ENDIAN = 1234	 # /* least-significant byte first (vax, pc) */
BIG_ENDIAN = 4321	 # /* most-significant byte first (IBM, net) */
PDP_ENDIAN = 3412	 # /* LSB first in word, MSW first in long (pdp)*/
BYTE_ORDER = sys.byteorder
