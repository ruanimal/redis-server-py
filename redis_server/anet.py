import socket
from typing import NewType, Tuple, Optional as Opt
from .csix import *

class AnetErr(Exception):
    pass

ANET_OK = 0
ANET_ERR = -1
ANET_ERR_LEN = 256

# /* Flags used with certain functions. */
ANET_NONE = 0
ANET_IP_ONLY = (1<<0)

# // 通用连接创建函数，被其他高层函数所调用
ANET_CONNECT_NONE = 0
ANET_CONNECT_NONBLOCK = 1

# 设置地址可重用
def anetSetReuseAddr(fd: socket.socket) -> None:
    fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

def anetTcpGenericConnect(addr: str, port: int, source_addr: str, flags: int) -> socket.socket:
    servinfo = socket.getaddrinfo(addr, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    s = None
    bound = 0
    # (family, type, proto, canonname, sockaddr)
    for sinfo in servinfo:
        try:
            s = socket.socket(sinfo[0], sinfo[1], sinfo[2])
        except OSError:
            continue
        anetSetReuseAddr(s)
        if source_addr:
            try:
                bservinfo = socket.getaddrinfo(source_addr, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except OSError:
                return s
            for info in bservinfo:
                try:
                    s.bind(info[4])
                    bound = 1
                    break
                except OSError:
                    continue
            if not bound:
                raise AnetErr('bind error')

        s.connect((addr, port))
        return s
    if not s:
        raise AnetErr('create socket fail')
    return s

# int anetTcpConnect(char *err, char *addr, int port);
# int anetTcpNonBlockConnect(char *err, char *addr, int port);
# int anetTcpNonBlockBindConnect(char *err, char *addr, int port, char *source_addr);
# int anetUnixConnect(char *err, char *path);
# int anetUnixNonBlockConnect(char *err, char *path);
# int anetRead(int fd, char *buf, int count);
# int anetResolve(char *err, char *host, char *ipbuf, size_t ipbuf_len);
# int anetResolveIP(char *err, char *host, char *ipbuf, size_t ipbuf_len);
# int anetTcpServer(char *err, int port, char *bindaddr, int backlog);
# int anetTcp6Server(char *err, int port, char *bindaddr, int backlog);
# int anetUnixServer(char *err, char *path, mode_t perm, int backlog);
# int anetTcpAccept(char *err, int serversock, char *ip, size_t ip_len, int *port);
# int anetUnixAccept(char *err, int serversock);
# int anetWrite(int fd, char *buf, int count);
# int anetNonBlock(char *err, int fd);
# int anetEnableTcpNoDelay(char *err, int fd);
# int anetDisableTcpNoDelay(char *err, int fd);
# int anetTcpKeepAlive(char *err, int fd);
# int anetPeerToString(int fd, char *ip, size_t ip_len, int *port);
# int anetKeepAlive(char *err, int fd, int interval);
# int anetSockName(int fd, char *ip, size_t ip_len, int *port);
