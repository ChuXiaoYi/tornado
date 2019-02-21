# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/19 下午4:59
#       @Author  : cxy =.= 
#       @File    : tornado_qps.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

from TokenBucket import TokenBucket
from config import limit_config

define("port", default=8000, help="run on the given port", type=int)


class IndexHandler(tornado.web.RequestHandler):
    async def get(self):
        queue_name = self.get_argument('queue', 'a')
        print(queue_name)

        bucket = self.application.bucket_dict[queue_name]
        # print("获得了一个bucket！")
        # print(bucket)
        token = bucket.produce()
        # print(f"现在桶里有几个：{bucket._capacity_list}")
        if token:
            result = bucket.consume(token)
            if result:
                self.write(str(result))
        else:
            self.write(str(False))

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler)
        ]
        super(Application, self).__init__(handlers, )
        self.bucket_dict = self.get_bucket_dict()


    def get_bucket_dict(self):
        """
        获取配置文件，实例化桶
        :return:
        """
        bucket_dict = dict()
        for source_name, conf in limit_config.items():
            bucket_dict.setdefault(source_name, TokenBucket(conf))
        print("实例化bucket成功！")
        return bucket_dict


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()