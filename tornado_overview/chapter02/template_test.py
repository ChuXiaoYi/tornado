# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/17 5:09 PM
#       @Author  : cxy =.= 
#       @File    : template_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import tornado
from tornado import web
from tornado.web import StaticFileHandler, RedirectHandler, template



class MainHandler(web.RequestHandler):
    """
    当客户端发起不同的http方法的时候，只需要重载handler中对应的方法即可
    """

    def cal_total(self, price, nums):
        """
        计算总价
        :param price:
        :param nums:
        :return:
        """
        return price * nums

    async def get(self, *args, **kwargs):
        # word = "hello cxy111"
        # t = template.Loader("/Users/chuxiaoyi/3-python/4-tornado/tornado/tornado_overview/chapter02/templates")
        # self.finish(t.load("hello.html").generate(word=word))

        orders = [
            {
                "name": "a",
                "image": "http://i1.mifile.cn/a1/T11lLgB5YT1RXrhCrK!40x40.jpg",
                "price": 0,
                "nums": 3,
                "detail": "<a href='http://www.baidu.com'>查看详情</a>"
            },
            {
                "name": "a",
                "image": "http://i1.mifile.cn/a1/T11lLgB5YT1RXrhCrK!40x40.jpg",
                "price": 39,
                "nums": 3,
                "detail": "<a href='http://www.baidu.com'>查看详情</a>"
            },
            {
                "name": "a",
                "image": "http://i1.mifile.cn/a1/T11lLgB5YT1RXrhCrK!40x40.jpg",
                "price": 39,
                "nums": 3,
                "detail": "<a href='http://www.baidu.com'>查看详情</a>"
            },

        ]

        self.render("index.html", orders=orders, cal_total=self.cal_total)

    def post(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass

setting = {
    "static_path": "/Users/chuxiaoyi/3-python/4-tornado/tornado/tornado_overview/chapter02/static",
    "static_url_prefix": "/static2/",
    "template_path": "templates"
}


if __name__ == '__main__':
    app = web.Application(
        [
            ("/", MainHandler),
            ("/2/", RedirectHandler, {'url': '/'}),
            ("/static/(.*)", StaticFileHandler, {"path": "/Users/chuxiaoyi/3-python/4-tornado/tornado/tornado_overview/chapter02/static"})
        ],
        debug=True,
        **setting
    )
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()