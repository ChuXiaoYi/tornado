# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 10:48 AM
#       @Author  : cxy =.= 
#       @File    : blockio_test.py
#       @Software: PyCharm
#       @Desc    : 阻塞io
# ---------------------------------------------
import requests

html = requests.get('https://www.baidu.com').content
print(html)

import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = 'www.baidu.com'
client.connect((host, 80))  # 阻塞io。这个时候cpu是空闲的
client.send(f'GET / HTTP/1.1\r\nHost:{host}\r\nConnection:close\r\n\r\n'.encode('utf8'))

data = b""
while 1:
    d = client.recv(1024)
    if d:
        data += d
    else:
        break

data = data.decode('utf8')
print(data)
