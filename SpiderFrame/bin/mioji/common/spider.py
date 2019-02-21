# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/21 下午3:16
#       @Author  : cxy =.= 
#       @File    : spider.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import abc
import uuid
from collections import defaultdict

from mioji.common.browser import MechanizeCrawler
from mioji.common.parser_except import ParserException


class Spider(object):
    """
    爬虫基类
    """
    source_type = ''                                    # 源类型
    targets = {}                                        # 抓取目标,例如:{'hotel':{}, 'room':{'version':'InsertNewFlight'}}
    old_spider_tag = {}                                 # 与老爬虫关联,例如:{'pricelineFlight': {'required': ['Flight']}}
    unable = False                                      # 不启用，默认启用
    queue_info = {}                                     # qps排队服务必要参数
    retry_info = {'max_try': 1, 'retry_codes': []}      # 重试配置

    def __init__(self, task=None):
        assert self.source_type != '', '缺失正确的抓取类型'
        assert self.targets != {}, '缺失正确的抓取 parser'
        assert len(self.targets) > 0, ParserException(1, '必须指明解析目标')
        self.task = task
        self.task_id = ""
        self.spider_taskinfo = {}
        self.is_verify = False
        self.need_proxy = True
        self.use_selenium = False
        self.browser = None
        self.__cpu_time = 0
        self.debug = True
        self.extra = {}
        self.user_datas = dict()
        self.verify_data = {'data': []}
        self._asy_temp_result = defaultdict(list)
        self.task_post_process_queue = None
        self.code = -1
        self.cost_crawl_time = None

        self._result = defaultdict(list)
        self.__targets_parser_func_dict = {}
        self.targets_required = self.targets
        self._crawl_targets_required = self.targets_required
        self.debug_info = {'pages': []}
        self.process_callback = None
        # 用于减少一次异步回调
        self.spider_frame_status = 0
        self.exception = None

        self.machine_type = None
        self.local_ip = None
        self.env = None

        for t in self.targets.keys():
            func_name = 'parse_' + t
            parse_func = getattr(self, func_name)
            self.__targets_parser_func_dict[t] = parse_func


    @abc.abstractmethod
    def targets_request(self):
        """
        用于定义请求链，每个子类爬虫必须重写这个方法
        Example::
                def targets_request(self):
                    @request(user_retry_count=1, proxy_type=PROXY_API, binding=['Flight'])
                    def get_flight():
                        req_info = {
                            'req': {
                                'method': 'get',
                                'url': ······,
                                'params': ·····
                            }
                        }
                        return req_info

                    yield get_flight
        :return:
        """
        pass

    def crawl(self):
        """
        外部启动爬虫的入口方法
        当调用这个方法时才能开始爬虫工作～
        :return:
        """
        # todo
        self.__create_broser()
        self.spider_taskinfo = dict(
            task_id=self.task.new_task_id if hasattr(self.task, 'new_task_id') else str(uuid.uuid1())
        )



    def __create_broser(self, create_new=False):
        """
        创建browser对象,赋值给当前的spider
        :return:
        """
        if not self.browser or create_new:
            if self.browser:
                self.browser.close()
                # 暂时通过机器类型判断
            if self.machine_type == "webdrive":
                # todo 这里需要改成SimulatorSpider啊啊啊啊别忘了啊啊啊啊啊
                # browser = SimulatorSpider()
                browser = MechanizeCrawler()
            else:
                browser = MechanizeCrawler()
            self.browser = browser
            return self.browser
        return self.browser


if __name__ == '__main__':
    spider = Spider()