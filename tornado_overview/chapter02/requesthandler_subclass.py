# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/17 4:54 PM
#       @Author  : cxy =.= 
#       @File    : requesthandler_subclass.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
from tornado.web import StaticFileHandler, RedirectHandler
import tornado
from tornado import web


class MainHandler(web.RequestHandler):
    """
    当客户端发起不同的http方法的时候，只需要重载handler中对应的方法即可
    """

    async def get(self, *args, **kwargs):
        self.write("hello world")

    def post(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass

setting = {
    "static_path": "/Users/chuxiaoyi/3-python/4-tornado/tornado/tornado_overview/chapter02/static",
    "static_url_prefix": "/static2/"
}


if __name__ == '__main__':
    app = web.Application(
        [
            ("/", MainHandler),
            ("/2/", RedirectHandler, {'url': '/'}),
            ("/static3/(.*)", StaticFileHandler, {"path": "/Users/chuxiaoyi/3-python/4-tornado/tornado/tornado_overview/chapter02/static"})
        ],
        debug=True,
        **setting
    )
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()