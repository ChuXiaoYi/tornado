# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/22 下午12:02
#       @Author  : cxy =.= 
#       @File    : request_parse.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import json
import random
import types
import datetime
import traceback
from typing import Iterable
from lxml import html as HTML
from collections import defaultdict

import requests
from logger import logger

from mioji.common import parser_except, store_utils
from mioji.common.utils import current_log_tag
from mioji.common.func_log import func_time_logger

PROXY_NONE = 0  # 不要代理
PROXY_FLLOW = 1  # 沿用上次的设置(遇到封禁 22、23框架会更换代理)
PROXY_FLLOW_HARD = 5  # 严格沿用上次的设置(遇到封禁 22、23框架会会重试但不会主动更换代理)
PROXY_REQ = 2  # 需要设置新代理
PROXY_REQ_FIRST = 3  # 第一次
PROXY_NEVER = 4  # 永远不用代理，一般api
PROXY_API = 6
PROXY_GOOGLE_MAPS = 7

slave_get_proxy = None
insert_db_dict = {}


def request(retry_count=3, proxy_type=PROXY_REQ, asynchronous=False, binding=None, user_retry_count=0,
            user_retry=False, multi=False, content_length=0, new_session=False, ip_type="test", ip_num=1,
            res_text='text'):
    """
    :param retry_count: 请求重试次数
    :param proxy_type: 代理类型
    :param asynchronous: 多个req是否需要同步
    :param binding: 绑定的解析函数，支持 None, str, bytes, callable, 以及可迭代的前几种类型
    :param user_retry: 用户重试，将重试部分教给用户操作。标记为 True 后，会增加 user_retry_err_or_resp handler 交由用户处理重试部分
    :param multi: 是否为同时进行多个解析。标记为 True 后，将会在爬取全部页面后返回所有页面值。在 parse 函数中返回的 req 和 data 分别为 list 。
    :param content_length: 是否需要判断 content_length 合法，None 不需要判断，0 或其他正整数，content_length 需要大于设置值
    :param new_session: 新的browser session
    :return: 返回 ReqParse 类型
    :ip_type: 决定使用国内代理(internal)还是国外(foreign)的
    """

    def call(func):
        req = ReqParse(func, proxy_type, asynchronous, binding, user_retry_count,
                       user_retry, multi, content_length, new_session, ip_type, ip_num, res_text)
        return req

    return call


class ReqParse(object):
    def __init__(self, func, proxy_type=PROXY_REQ, asynchronous=False, binding=None, user_retry_count=0,
                 user_retry=False, multi=False, content_length=0, new_session=False, ip_type="test", ip_num=1,
                 res_text='text'):
        self.__request_func = func
        self.retry_count = user_retry_count if user_retry_count else 4  # 强制4次重试
        self.res_text = res_text  # 解析格式
        self.proxy_type = proxy_type
        self.asynchronous = asynchronous
        self.binding = binding
        self.req_count = 0

        self.request_template = None
        self.__result = None
        self.spider = None
        self.user_retry = user_retry
        self.user_exc = False
        self.need_content_length = content_length

        self.multi = multi  # 是否返回此种类型所有页面

        self.is_forbidden = False  # 初始化抓取标志
        self.req_exception = None
        self.proxy = None
        self.content_length = 0

        self.ip_type = ip_type  # 代理ip所需类型，国内or国外

        self.ip_num = ip_num  # 代理ip请求数量

        self.new_session = new_session  # session browser

    @property
    def request_func(self):
        return self.__request_func

    def request(self):
        return self.__request_func()

    def __crawl_data_str(self, request_template, browser):
        resp = None
        try:
            # 使用方法修改，用户直接修改 request_template 中的值
            self.spider.prepare_request(request_template)

            # 获得 request_template 中的 req
            req = request_template['req']

            # 用于控制qps
            if hasattr(self.spider, 'queue_info'):
                browser.queue_info = self.spider.queue_info

            if hasattr(self.spider.task, 'req_qid'):
                browser.qid = self.spider.task.req_qid
            else:
                browser.qid = ""
            browser.task_id = self.spider.task.task_id
            browser.source = self.spider.task.source
            browser.tid = self.spider.task.tid
            browser.ori_type = self.spider.task.ori_type

            resp = browser.req(**req)
            # 网络错误，异常抛出
            resp.raise_for_status()

            content_length = len(resp.content)
            if isinstance(self.need_content_length, int):
                logger.debug(
                    current_log_tag() + '[爬虫 content_length={1} 检测][页面长度需要大于 {0}]'.format(self.need_content_length,
                                                                                          content_length))
                if content_length <= self.need_content_length:
                    raise parser_except.ParserException(parser_except.PROXY_INVALID, msg='data is empty')
            elif self.need_content_length is None:
                logger.debug(current_log_tag() + '[爬虫无需 content_length 检测]')
            else:
                logger.debug(
                    current_log_tag() + '[未知 content_length 检测类型][type: {0}]'.format(
                        str(type(self.need_content_length))))
            return resp, content_length
        # timeout
        except requests.exceptions.SSLError as e:
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_SSL, msg=str(e), error=e)
        except requests.exceptions.ProxyError as e:  # 代理失效
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_INVALID, msg='Proxy Error', error=e)

        except requests.exceptions.ConnectTimeout as e:
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_FORBIDDEN, msg='Request connect Timeout', error=e)
        except requests.exceptions.ReadTimeout as e:
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_FORBIDDEN, msg='Request read Timeout', error=e)
        except requests.exceptions.Timeout as e:
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_FORBIDDEN, msg='Request Timeout', error=e)

        except requests.exceptions.ConnectionError as err:
            self.spider.response_error(request_template, resp, err)
            raise parser_except.ParserException(parser_except.PROXY_INVALID, msg=str(err))

        except requests.exceptions.HTTPError as err:  # 4xx 5xx 的错误码会catch到
            self.spider.response_error(request_template, resp, err)
            raise parser_except.ParserException(parser_except.PROXY_INVALID, msg=str(err), error=err)

        except requests.exceptions.RequestException as err:  # 这个是总的error
            self.spider.response_error(request_template, resp, err)
            raise parser_except.ParserException(parser_except.PROXY_INVALID, msg=str(err), error=err)
        except Exception as e:  # 这个是最终的error
            self.spider.response_error(request_template, resp, e)
            raise parser_except.ParserException(parser_except.PROXY_INVALID, msg=traceback.format_exc())

    def crawl_data(self, request_template, browser, source_name):
        """
        页面抓取函数
        :param request_template: 请求字典
        :param browser: 抓取浏览器
        :param source_name: 源名称
        :return: 返回抓取结果 response 对象
        """
        try:
            logger.debug(current_log_tag() + 'crawl %s, retry_count: %s', self.__request_func.__name__, self.req_count)
            # 代理装配
            self.browser_set_proxy(browser, source_name)

            resp, self.content_length = self.__crawl_data_str(request_template, browser)

            # todo 修改 user_retry 返回的结果
            if self.user_retry:
                try:
                    user_check = self.spider.user_retry_err_or_resp(resp, self.req_count, request_template, False)
                except Exception as e:
                    self.user_exc = True
                    raise e

                # 当用户返回 True 时
                if user_check:
                    return resp
                else:
                    raise parser_except.ParserException(parser_except.PROXY_INVALID,
                                                        '代理异常')
            else:
                return resp
        except parser_except.ParserException as e:
            self.is_forbidden = e.code in (
                parser_except.PROXY_FORBIDDEN, parser_except.PROXY_FORBIDDEN, parser_except.REQ_ERROR)
            self.req_exception = e
        except Exception as e:
            self.req_exception = parser_except.ParserException(parser_except.REQ_ERROR, 'req exception:{0}'.format(e))

            # 如果有用户异常，则置位用户重试
            if self.user_exc:
                if isinstance(e, parser_except.ParserException):
                    self.req_exception = e

        finally:
            if self.req_exception:
                code = self.req_exception.code
            else:
                code = 0

        if self.req_exception:
            raise self.req_exception

    @func_time_logger
    def convert(self, request_template, data):
        data_con = request_template.get('data', {})
        c_type = data_con.get('content_type', 'string')
        logger.debug(current_log_tag() + 'Converter got content_type: %s', c_type)
        if c_type is 'html':
            return HTML.fromstring(data)
        elif c_type is 'json':
            return json.loads(data)
        elif isinstance(c_type, types.MethodType):
            try:
                return c_type(request_template, data)
            except:
                raise parser_except.ParserException(-1, 'convert func muset error{0} ,func：{1}'.format(
                    traceback.format_exc(), c_type))
        else:
            return data

    def browser_set_proxy(self, browser, source_name):
        # 不使用代理、永远不使用代理
        if self.proxy_type == PROXY_NONE or self.proxy_type == PROXY_NEVER:
            browser.set_proxy(None)

        # 严格使用上次代理
        if self.proxy_type == PROXY_FLLOW_HARD:
            pass
        elif self.proxy_type == PROXY_API:
            browser.set_proxy({"PROXY_API": {'http': 'http://10.10.16.68:3128', 'https': 'https://10.10.16.68:3128'}})
        elif self.proxy_type == PROXY_GOOGLE_MAPS:
            google_maps_proxy = random.choice(["10.11.105.46:8888", "10.11.37.111:8888"])
            browser.set_proxy(
                {"PROXY_GOOGLE_MAPS": {"http": "http://" + google_maps_proxy, "https": "https://" + google_maps_proxy}})
        # 请求代理 或 "被封禁 且 不是永远不使用代理" 主动设置代理
        elif self.proxy_type == PROXY_REQ or self.is_forbidden:
            verify_info = self.spider.machine_type
            proxy_info = w_get_proxy(self.spider.debug, source=source_name, task=self.spider.task,
                                     verify_info=verify_info)
            browser.req_count = self.req_count

            if proxy_info != "REALTIME" and proxy_info:
                self.proxy = proxy_info
                self.spider.proxy = self.proxy
                out_ip = proxy_info[-1]
                browser.proxy_inf = out_ip
                if isinstance(out_ip, list):
                    out_ip = json.loads(out_ip[0])['resp'][0]['ips'][0]['external_ip']
                    browser.out_ip = out_ip
                else:
                    browser.out_ip = ""
                proxy = proxy_info[0]
            else:
                proxy = proxy_info
            browser.set_proxy(proxy)

    @func_time_logger
    def parse(self, request_template, targets_bind, converted_data, page_index, required=None, multi_last=False):
        result = defaultdict(list)
        parsed = set()
        if not multi_last:
            parser_list = request_template.get('user_handler', [])
            for parser in parser_list:
                if parser not in parsed:
                    logger.debug(current_log_tag() + 'user parser %s', parser)
                    parser(request_template, converted_data)

        # 通过 parse 更新 result 信息
        def parse_result(parser):
            # 判断是否为有解析需要，且在需解析目标中
            parser_name = parser.__name__.split('_', 1)[1]
            if parser_name in required:
                logger.debug(current_log_tag() + 'parse target %s', parser_name)

                per_result = parser(request_template, converted_data)
                if per_result is not None:
                    if per_result:
                        start = datetime.datetime.now()
                        if isinstance(per_result, list):
                            # 添加 guest_info
                            store_utils.add_index_info(
                                self.spider.targets.get(parser_name, {}).get('version', None),
                                per_result, page_index)
                            # 添加 stopby 信息
                            store_utils.add_stop_by_info(
                                self.spider.targets.get(parser_name, {}).get('version', None),
                                per_result, self.spider.task)
                            result[parser_name].extend(per_result)
                        elif isinstance(per_result, dict):
                            result[parser_name].append(per_result)
                        logger.debug(
                            current_log_tag() + '[结果保存][不使用压缩][用时： {0} ]'.format(
                                datetime.datetime.now() - start))

        # 解析目标，酒店、房间、等
        # for target, parser in targets_bind.items():
        if isinstance(self.binding, Iterable) and not isinstance(self.binding, (str, bytes)):
            for binding in self.binding:
                # 对 binding 种类进行兼容判断
                if binding is None:
                    continue
                elif isinstance(binding, (str, bytes)):
                    parser = targets_bind.get(binding, '')
                    if parser == '':
                        TypeError('无法从 targets 中获取 parser {0}'.format(binding))
                elif callable(binding):
                    parser = binding
                else:
                    raise TypeError('不支持绑定类型 {0} 的 {1}'.format(type(binding), repr(binding)))
                # 更新 result 信息
                parse_result(parser)

        elif isinstance(self.binding, (str, bytes)):
            parser = targets_bind.get(self.binding, '')
            if parser == '':
                TypeError('无法从 targets 中获取 parser {0}'.format(self.binding))

            # 更新 result 信息
            parse_result(parser)

        elif callable(self.binding):
            parser = self.binding
            # 更新 result 信息
            parse_result(parser)

        return result

# other
def w_get_proxy(debug, source, task, verify_info):
    if debug and not slave_get_proxy:
        print('debug，and not define get_proxy，so can’t get proxy ')
        return None
    p = slave_get_proxy(source=source, task=task, verify_info=verify_info)
    if not p:
        raise parser_except.ParserException(parser_except.PROXY_NONE, f'get {source} proxy None')
    return p