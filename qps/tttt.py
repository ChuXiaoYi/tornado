# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/19 下午7:10
#       @Author  : cxy =.= 
#       @File    : tttt.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
from gevent import monkey;monkey.patch_all()
import requests
import datetime
from gevent.pool import Pool

def req():
    print(f'开始时间：{datetime.datetime.utcnow()}')
    response = requests.get('http://127.0.0.1:8000').content
    print(f'结果：{response}')
    print(f'结束时间：{datetime.datetime.utcnow()}')

p = Pool(10)
for i in range(1000):
    p.apply_async(req)

p.join()