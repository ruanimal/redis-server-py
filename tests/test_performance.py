import subprocess
import time
from redis import Redis

def test_set():
    conn = Redis(port=5678)
    now = time.time()
    for i in range(10000):
        conn.set('test{}'.format(i), i)
    print(time.time() - now)
