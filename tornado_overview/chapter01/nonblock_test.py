# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 11:05 AM
#       @Author  : cxy =.= 
#       @File    : nonblock_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.setblocking(False)
host = 'www.baidu.com'
try:
    client.connect((host, 80))  # 阻塞io。这个时候cpu是空闲的
except BlockingIOError as e:
    pass

while 1:
    try:
        client.send(f'GET / HTTP/1.1\r\nHost:{host}\r\nConnection:close\r\n\r\n'.encode('utf8'))
        print('send success')
        break
    except OSError as e:
        pass

data = b""
while 1:
    try:
        d = client.recv(1024)
    except BlockingIOError as e:
        continue
    if d:
        data += d
    else:
        break

data = data.decode('utf8')
print(data)
