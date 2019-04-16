# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 11:48 AM
#       @Author  : cxy =.= 
#       @File    : select_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import socket
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE

selector = DefaultSelector()


class Fetcher(object):

    def readable(self, key):
        d = self.client.recv(1024)
        if d:
            self.data += d
        else:
            selector.unregister(key.fd)
            data = self.data.decode('utf8')
            print(data)

    def connected(self, key):
        selector.unregister(key.fd)
        host = 'www.baidu.com'
        self.client.send(f'GET / HTTP/1.1\r\nHost:{host}\r\nConnection:close\r\n\r\n'.encode('utf8'))
        selector.register(self.client.fileno(), EVENT_READ, self.readable)

    def get_url(self, url):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.setblocking(False)
        self.data = b""
        host = 'www.baidu.com'
        try:
            self.client.connect((host, 80))  # 阻塞io。这个时候cpu是空闲的
        except BlockingIOError as e:
            pass

        selector.register(self.client.fileno(), EVENT_WRITE, self.connected)


def loop_forever():
    while 1:
        ready = selector.select()
        for key, mask in ready:
            call_back = key.data
            call_back(key)


if __name__ == '__main__':
    fetcher = Fetcher()
    url = 'https://www.baidu.com'
    fetcher.get_url(url)
    loop_forever()