# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/21 下午3:16
#       @Author  : cxy =.= 
#       @File    : spider.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import abc
import json
import time
import traceback
import types
import uuid
from collections import defaultdict

from logger import logger

from mioji.common.func_log import func_time_logger
from mioji.common.pool import pool
from mioji.common import parser_except
from mioji.common.pool_event_lock import block_async
from mioji.common.browser import MechanizeCrawler
from mioji.common.parser_except import ParserException
from mioji.common.utils import current_log_tag, get_md5
from mioji.common.request_parse import request, w_get_proxy

PROXY_NONE = 0  # 不要代理
PROXY_FLLOW = 1  # 沿用上次的设置(遇到封禁 22、23框架会更换代理)
PROXY_FLLOW_HARD = 5  # 严格沿用上次的设置(遇到封禁 22、23框架会会重试但不会主动更换代理)
PROXY_REQ = 2  # 需要设置新代理
PROXY_REQ_FIRST = 3  # 第一次
PROXY_NEVER = 4  # 永远不用代理，一般api
PROXY_API = 6
PROXY_GOOGLE_MAPS = 7

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

    def response_error(self, req, resp, error):
        """
        请求异常
        :param resp requests response
        :param error 异常
        """

        pass

    def response_callback(self, req, resp):
        """
        resp.url 判断是否是抓取页面或其他
        """
        pass

    def prepare_request(self, request_template):
        """
        在抓取过程中由用户指定 req，用户在函数中直接修改
        :param request_template: 本次请求的 request_template
        """
        pass

    # todo
    # @property
    # def task(self):
    #     return self._task
    #
    # @task.setter
    # def task(self, task):
    #     if self.source_type.endswith('ListHotel') and task:
    #         task = task_change_city(self.source_type, task)
    #     if self.source_type.endswith('Hotel') and task and "List" not in self.source_type:
    #         task = task_change_sass(task)
    #     self._task = task

    def crawl(self):
        """
        外部启动爬虫的入口方法
        当调用这个方法时才能开始爬虫工作～
        :return:
        """
        # todo
        self.__create_browser()
        cur_id = str(uuid.uuid1())
        if hasattr(self.task, 'new_task_id'):
            cur_id = self.task.new_task_id
        self.spider_taskinfo = {'task_id': cur_id}
        for k, v in self.task.__dict__.items():
            self.spider_taskinfo[k] = v
            try:
                logger.info(current_log_tag() + '[任务信息][%s][%s]' % (k, json.dumps(v)))
            except Exception:
                continue
        chains = self.targets_request()
        try:
            self.code = self.__crawl_by_chain(chains)
        except parser_except.ParserException as e:
            logger.exception(e)
            self.code = e.code
            self.exception = e.msg
            if e.retry_from_first:
                raise e

        # 通过返回的全部 result 判断错误码
        self.check_all_result()
        return self.code



    def __create_browser(self, create_new=False):
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

    def __crawl_by_chain(self, chains):
        """
        根据请求链的类型，进入不同的抓取顺序进行抓取
        :param chains:
        :return:
        """
        code = 0
        try:
            for reqParse in chains:
                # gevent.sleep(0)
                browser = self.__create_browser(reqParse.new_session)
                reqParse.spider = self
                t_req = reqParse.request()

                if isinstance(t_req, dict):  # 单一请求
                    new_result = self.__single_crawl(reqParse, browser, t_req, 0)

                elif isinstance(t_req, list):
                    # 爬虫有可能返回一个空列表！！！
                    if t_req:
                        if reqParse.asynchronous:  # 并行抓取
                            list_result = self.__async_crawl_list(reqParse, browser, t_req)
                        else:  # 串行请求
                            list_result = self.__crawl_list(reqParse, browser, t_req)
                        new_result, code = self.check_list_result(list_result, code)  # $$$ 可以优化

                elif isinstance(t_req, types.GeneratorType):  # 针对使用的yelid 调用方法的请求
                    list_result = self.__crawl_list(reqParse, browser, t_req)
                    new_result, code = self.check_list_result(list_result, code)

                self.__spider_append_result(new_result)

            if self.use_selenium and browser.br:
                browser.close()
        except parser_except.ParserException as e:
            if self.use_selenium and browser.br:
                browser.close()
            logger.error(e)
            raise e
        except Exception:
            if self.use_selenium and browser.br:
                browser.close()
            logger.exception(
                current_log_tag() + '[新框架 持续请求 未知问题][ {0} ]'.format(traceback.format_exc().replace('\n', '\t')))
            raise parser_except.ParserException(parser_except.UNKNOWN_ERROR, 'e:{0}'.format(traceback.format_exc()))

        return code

    def __single_crawl(self, reqParse, browser, request_template, page_count):
        """ 用于请求的基本方法
        """
        # 请求链中的header 可以被沿用
        headers = request_template['req'].get('headers', None)
        use_headers = request_template['req'].get('use_headers', False)
        if headers:
            browser.add_header(headers, use_headers)

        # 设置 res 的 默认值
        res = defaultdict(list)

        # 初始化请求参数

        local_req_count = 0
        reqParse.req_count = 0
        reqParse.is_forbidden = False
        reqParse.req_exception = None
        reqParse.proxy = None
        reqParse.content_length = 0

        self.__cpu_time += time.time() * 1000

        while local_req_count < reqParse.retry_count:
            # 增加一次重试次数
            local_req_count += 1
            logger.debug(current_log_tag() + '[开始抓取][ {0} ]'.format(request_template['req'].get('url', '')))
            # 外部传入请求次数，用于在 parse 过程中抛出的代理异常进行重新抓取
            try:
                resp = reqParse.crawl_data(request_template, browser, self.task.source)
            except parser_except.ParserException as e:
                traceback.print_exc()
                if reqParse.user_exc:
                    # 抛出用户在函数中抛出的错误
                    raise e
                # 错误码21/22/23 或 开发指定需要重试
                if e.code in (parser_except.PROXY_FORBIDDEN, parser_except.PROXY_INVALID, parser_except.REQ_ERROR,
                              parser_except.PROXY_SSL) or e.need_retry:
                    reqParse.is_forbidden = True

                    if local_req_count >= reqParse.retry_count or e.retry_from_first:
                        raise e
                    else:
                        logger.debug(current_log_tag() + traceback.format_exc())
                        logger.debug(current_log_tag() + '[准备重试][错误由框架抛出][错误码：{0}][count:{1}]'.format(e.code,
                                                                                                      reqParse.req_count))
                        continue
                else:
                    raise e
            except Exception as e:
                if reqParse.user_exc:
                    # 抛出用户在函数中抛出的错误
                    raise e
                if local_req_count >= reqParse.retry_count:
                    raise e
                else:
                    continue

                    # 请求中增加 resp 的值
            request_template['resp'] = resp
            # 打印存储抓取结果
            self.response_callback(request_template, resp)
            if reqParse.res_text == 'text':
                res = resp.text
            else:
                res = resp.content
            try:
                logger.debug(
                    current_log_tag() + '[抓取结果][ {2} ][ {0} ... ... {1} ]'.format(res[:100], res[-100:],
                                                                                  request_template['req'][
                                                                                      'url']).replace('\n',
                                                                                                      '').replace(
                        '\t', ''))
            except Exception:
                pass
            # 如果本地运行，将不执行上传操作
            if not self.debug and self.env != "local":
                md5_key = get_md5(res)
                verify_task_info = {
                    'func_name': reqParse.request_func.__name__,
                    'page_index': page_count,
                    'retry_count': local_req_count - 1,
                    'md5_key': md5_key
                }
                # 把上传抓取页面至ucloud
                self.task_post_process_queue.put((res, self.task, md5_key))
                self.verify_data['data'].append(verify_task_info)

            point_time = time.time() * 1000
            try:
                convert_data = reqParse.convert(request_template, res)
            except Exception:
                if local_req_count >= reqParse.retry_count:
                    logger.debug(current_log_tag() + traceback.format_exc())
                    raise parser_except.ParserException(parser_except.DATA_FORMAT_ERROR,
                                                        '[traceback: {0}]'.format(traceback.format_exc()))
                else:
                    continue
            finally:
                self.__cpu_time += time.time() * 1000 - point_time

            # 数据解析部分
            point_time = time.time() * 1000
            try:
                res = reqParse.parse(request_template, self.__targets_parser_func_dict, convert_data, page_count,
                                     self._crawl_targets_required)

                break
            except parser_except.ParserException as e:
                if e.code in (parser_except.PROXY_FORBIDDEN, parser_except.PROXY_INVALID):
                    reqParse.is_forbidden = True

                    if local_req_count >= reqParse.retry_count or e.retry_from_first:
                        raise e
                    else:
                        logger.debug(current_log_tag() + '[准备重试][错误由爬虫抛出][错误码：{0}]'.format(e.code))
                        convert_data = None
                        continue
                else:
                    raise e
            except Exception:
                raise parser_except.ParserException(parser_except.PARSE_ERROR,
                                                    '[traceback:{0}]'.format(traceback.format_exc()))
            finally:
                self.__cpu_time += time.time() * 1000 - point_time
                self.response_callback(request_template, resp)
        have_ticket = False
        for k, v in res.items():
            if not v:
                continue
            self._asy_temp_result[k] += v
            have_ticket = True
        # 有票 && slave调用的爬虫才会异步回调
        if have_ticket and self.process_callback and not self.debug and self.env != "local":
            self.process_callback(task=self.task, spider=self, result_type="RUNNING")

        return res


    def __async_crawl_list(self, reqParse, browser, req_list):
        """
        并行抓取分页
        丢到协程池里
        """

        a_result = defaultdict(list)
        all_except = True
        all_ok = True
        one_exception = None

        params = []
        total_count = 0
        for req in req_list:
            total_count += 1
            params.append((reqParse, browser, req, total_count))

        result = block_async(pool, self.__single_crawl, params)

        success_count = 0
        error_req = []
        for a_res in result:
            err_or_data, is_data = a_res
            if is_data:
                success_count += 1
                all_except = False
                self.__target_append_result(a_result, err_or_data)
            else:
                all_ok = False
                args, kwargs, one_exception = err_or_data
                if hasattr(one_exception, 'retry_from_first') and one_exception.retry_from_first:
                    raise one_exception
                error_req.append((args[2], one_exception.message))
        if reqParse.binding:
            self.success_count = success_count
            self.all_count = total_count
        logger.debug(current_log_tag() + '[翻页抓取][并行抓取][ 成功 {0} / {1} ]'.format(success_count, total_count))
        if error_req:
            logger.debug(current_log_tag() + '[翻页抓取][并行抓取][ 失败页请求 {0} ]'.format(str(error_req)))
        return a_result, all_except, all_ok, one_exception

    def __crawl_list(self, reqParse, browser, req_list):
        """
        串行抓取分页
        """
        result = defaultdict(list)
        all_except = True
        all_ok = True
        one_exception = None

        total_count = 0
        success_count = 0
        error_req = []
        for req in req_list:
            # 串行增加翻页限制取消
            # if NEED_FLIP_LIMIT:
            #     if total_count >= MAX_FLIP:
            #         break
            total_count += 1
            try:
                success_count += 1
                res = self.__single_crawl(reqParse, browser, req, page_count=total_count)
                self.__target_append_result(result, res)
                all_except = False
            except Exception as e:
                all_ok = False
                one_exception = e
                error_req.append((req, one_exception.message))
                logger.exception(
                    current_log_tag() + '[新框架][页面解析异常][ {0} ]'.format(traceback.format_exc().replace('\n', '\t')))

                #  抛出生成器部分的异常
                if isinstance(req, types.GeneratorType):
                    raise e
        if reqParse.binding:
            self.success_count = success_count
            self.all_count = total_count
        logger.debug(current_log_tag() + '[翻页抓取][串行抓取][ 成功 {0} / {1} ]'.format(success_count, total_count))
        if error_req:
            logger.debug(current_log_tag() + '[翻页抓取][串行抓取][ 失败页请求 {0} ]'.format(str(error_req)))
        return result, all_except, all_ok, one_exception

    def check_list_result(self, list_result, code):
        """

        $$$ 得优化 $$$
        检查每一个请求项返回的页面内容
        :param list_result: result, all_except, all_ok, one_exception 传入四项参数，返回的结果列表，是否全部为异常，是否全部正常
        :return:
        result like:{'hotelList_room':[(),()]}
        code: 0 全部正确；36 有翻页错误
        """

        result, all_except, all_ok, one_exception = list_result
        if all_ok and not all_except:
            if result:
                code_res = 0
            else:
                code_res = 0
        elif result and not all_except:
            code_res = 36
        elif not all_except:
            code_res = 0
        else:
            code_res = 37
        if code == 0:
            code = code_res
        if code == 37 and code_res == 0:
            code = 36

        return result, code

    def __spider_append_result(self, new_result):
        """
        向 self.result 中添加解析结果
        :param new_result: 必须为解析结果
        :return: None
        :调用回调方法
        """

        for k, v in new_result.items():
            if not v:
                continue
            data_bind = self.targets[k].get('bind', None)
            if data_bind:
                logger.debug("current_log_tag() + [ 抓取绑定 {0} ][ 数据绑定 {1} ]".format(k, data_bind))
                self._result[data_bind] += v
                logger.debug(current_log_tag() + "%s, length=%s, all=%s", k, len(v), len(self._result.get(k, [])))
            else:
                self._result[k] += v
                logger.debug(current_log_tag() + "%s, length=%s, all=%s", k, len(v), len(self._result.get(k, [])))

    def check_all_result(self):
        """
        在其中判断全部 result 的状态码，爬虫可以重写
        self.result 为返回的所有结果
        self.code 为将要返回的状态码
        :return: 无需返回，直接修改 self.code 即可
        """
        # 只针对误判的 0 进行操作
        if self.code == 0:
            # 默认通过数据状况判断 29
            if not self.result:
                self.code = 29

            for k, v in self.result.items():
                if not v:
                    self.code = 29

        if self.code == 29:
            if self.result:
                for k, v in self.result.items():
                    if v:
                        self.code = 36

    @staticmethod
    def __target_append_result(result, new_result):
        """
        向 result 中添加数据
        :param result: 被添加量
        :param new_result: 添加量
        :return: None
        : 此处用了字典的单例。
        """
        for k, v in new_result.items():
            if not v:
                continue
            logger.debug(current_log_tag() + "%s, length=%s, all=%s", k, len(v), len(result.get(k, [])))
            result[k] += v

    @property
    @func_time_logger
    def result(self):
        try:
            for k, v in self._result.items():
                logger.debug(current_log_tag() + '[抓取结果][key: {0}][value_len: {1}]'.format(k, len(v)))
        except Exception:
            pass
        return self._result

if __name__ == '__main__':
    spider = Spider()