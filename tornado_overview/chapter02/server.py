# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/17 1:37 PM
#       @Author  : cxy =.= 
#       @File    : server.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import time

import tornado
from tornado import web


class MainHandler(web.RequestHandler):
    """
    当客户端发起不同的http方法的时候，只需要重载handler中对应的方法即可
    """

    async def get(self, *args, **kwargs):
        time.sleep(5)
        self.write("hello world")

    def post(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass


if __name__ == '__main__':
    app = web.Application(
        [
            ("/", MainHandler)
        ],
        debug=True
    )
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
