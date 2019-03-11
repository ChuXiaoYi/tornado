# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/21 上午10:01
#       @Author  : cxy =.=
#       @File    : slave.py
#       @Software: PyCharm
#       @Desc    :
# ---------------------------------------------
import json

import tornado.web
import tornado.httpserver
import tornado.ioloop

from tornado.options import define, options

from celeryd import spider_crawl
from mioji.common.task_info import Task



define('port', default=8001, type=int, help="the ports of slave")


class WebHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        task_list = self.parse_task()
        for task in task_list:
            # todo 从spider_factory中取当前task对应的spider，进行爬取
            spider_crawl.delay(task.source)

        result = {'result': '0', 'task': []}
        self.write(result)


    def parse_task(self):
        result = list()

        qid = self.get_argument('qid')
        tid = self.get_argument('tid')
        uid = self.get_argument('uid')
        type = self.get_argument('type')
        ptid = self.get_argument('ptid')
        role = self.get_argument('role')
        csuid = self.get_argument('csuid')
        ori_type = self.get_argument('ori_type')
        req_list = json.loads(self.get_argument('req'))
        client_ip = self.request.remote_ip

        for req in req_list:
            task = Task()
            task.req_qid = qid
            task.req_uid = uid
            task.order_no = req.get('order_no', '')
            task.source = req['source']
            task.content = req['content']
            task.deadline = req.get('deadline', 0)
            task.debug = req.get('debug', False)
            task.tid = tid
            task.client_ip = client_ip
            task.ori_type = ori_type
            task.ticket_info = req['ticket_info']
            task.verify = req.get('verify', {'type': 'pre', 'set_type': 'E'})
            task.req_md5 = task.ticket_info.get('md5', 'default_md5')

            task.master_info = req.get('master_info', 'default_host')
            task.host = task.master_info.get('master_addr')

            task.redis_host = task.master_info.get('redis_addr').split(':')[0]
            task.redis_port = task.master_info.get('redis_addr').split(':')[-1]

            task.redis_db = task.master_info.get('redis_db')
            task.redis_passwd = task.master_info.get('redis_passwd')

            task.req_qid_md5 = task.req_qid + '-' + task.req_md5
            task.other_info = req.get('other_info', {})

            callback_type = 'scv100'
            if 'callback_type' in task.other_info:
                callback_type = task.other_info['callback_type']

            task.callback_type = callback_type
            redis_key_list = task.other_info.get('redis_key', [])
            # 之前redis_key 会传多个过来，现在只传一个，但保留了list的格式
            for each in redis_key_list:
                task.redis_key = each
                task.other_info['redis_key'] = each
                # logger.info('s[{0}] id[{1}]new verify task:{2}'.format(task.source, task.new_task_id, task))
                yield task


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/rtquery', WebHandler)
        ]
        super(Application, self).__init__(handlers)
        self.initialize()

    def initialize(self):
        """
        加载全局配置
        :return:
        """

        # todo 开启心跳
        pass

if __name__ == '__main__':
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop().current().start()
