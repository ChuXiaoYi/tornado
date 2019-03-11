# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/3/6 下午12:08
#       @Author  : cxy =.= 
#       @File    : celeryd.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
from celery import Celery

from mioji.common.spider_factory import SpiderFactory

app = Celery('tasks', broker='pyamqp://guest@localhost//', backend='redis://localhost')
# 初始化工厂，将全部spider加载到全局环境中
app.spider_factory = SpiderFactory()
app.spider_factory.load()

@app.task
def spider_crawl(source):
    print(app.spider_factory)