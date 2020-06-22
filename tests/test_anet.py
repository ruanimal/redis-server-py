from redis_server.anet import anetTcpServer, anetTcpConnect
from threading import Thread

def echo_server(sock):
    def echo_handler(address, client_sock):
        print('Got connection from {}'.format(address))
        while True:
            msg = client_sock.recv(8192)
            if not msg:
                break
            client_sock.sendall(msg)
        client_sock.close()

    while True:
        client_sock, client_addr = sock.accept()
        echo_handler(client_addr, client_sock)

def test_anetTcpServer():
    s = anetTcpServer(0, '127.0.0.1', 0)
    s_addr, s_port = s.getsockname()
    t = Thread(target=echo_server, args=(s,))
    t.setDaemon(True)
    t.start()
    c = anetTcpConnect(s_addr, s_port)
    msg = b'1' * 100
    c.sendall(msg)
    assert c.recv(1000) == msg
