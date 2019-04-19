# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/17 1:58 PM
#       @Author  : cxy =.= 
#       @File    : urlconfig.py
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
        # time.sleep(5)
        self.redirect(self.reverse_url("people_id", 1))

    def post(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass


class PeopleIdHandler(web.RequestHandler):
    def initialize(self, name):
        """
        初始化
        :param name:
        :return:
        """
        self.db_name = name

    async def get(self, id, *args, **kwargs):
        self.write(f"用户id：{id} db_name: {self.db_name}")


class PeopleNameHandler(web.RequestHandler):
    async def get(self, name, *args, **kwargs):
        self.write(f"用户name：{name},")


class PeopleInfoHandler(web.RequestHandler):
    async def get(self, name, age, gender, *args, **kwargs):
        self.write(f"用户name：{name}, 用户age：{age}, 用户gender：{gender}, ")


people_db = {"name": "people"}

urls = [
    web.URLSpec("/", MainHandler, name="index"),
    # web.URLSpec("/people/(\d+)/?", PeopleIdHandler, people_db, name="people_id"),# 配置如/people/1/
    web.URLSpec("/people/(?P<id>\d+)/?", PeopleIdHandler, people_db, name="people_id"),  # 配置如/people/1/
    web.URLSpec("/people/(\w+)/?", PeopleNameHandler, name="people_name"),  # 配置如/people/a/
    web.URLSpec("/people/(\w+)/(\d+)/(\w+)/?", PeopleInfoHandler, name="people_info"),  # 配置如/people/name/age/gender/

]

if __name__ == '__main__':
    app = web.Application(urls, debug=True)
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
