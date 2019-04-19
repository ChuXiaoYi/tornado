# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/17 3:42 PM
#       @Author  : cxy =.= 
#       @File    : requesthandler_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import json
import tornado

from tornado import web, options
from tornado.web import RequestHandler


class MainHandler(RequestHandler):
    # def initialize(self, db):
    #     """
    #     用于初始化handler类的过程
    #     :return:
    #     """
    #     self.db = db

    def prepare(self):
        """
        用于真正调用请求之前的初始化方法
        例如：在请求get之前，要先经过这个方法
        可以做：
            1 打印日志， 打开文件
        :return:
        """
        pass

    def on_finish(self):
        """
        请求结束
        可以做：
            关闭句柄， 清理内存
        :return:
        """
        pass

    def get(self, *args, **kwargs):
        """
        这里处理http请求
        :param args:
        :param kwargs:
        :return:
        """

        # 获取用户输入
        try:
            param = json.loads(self.request.body.decode("utf8"))    # 获取json数据
            data1 = self.get_query_argument("name")
            data2 = self.get_query_arguments("name")
            data3 = self.get_arguments("name")
        except Exception as e:
            self.set_status(500)
        # self.write(data1, data2, data3)

people_db = {"name": "people"}

urls = [
    web.URLSpec("/", MainHandler, name="index")
]

if __name__ == '__main__':
    app = web.Application(urls, debug=True)
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()


