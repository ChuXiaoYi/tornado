# !/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
import json
import time
import pytz

from lxml import etree

import ErrNumber
from bed_type_json import bed_type_dict
from mioji.common.logger import logger
from mioji.common.class_common import Room
from mioji.common import parser_except
from mioji.common.spider import Spider, request, PROXY_API
from mioji.common.task_info import Task
from mioji.common.check_book.check_book_ratio import use_record_api
from mioji.common.browser import getuid

TEST_API_URL = "http://api.didatravel.com/Services/WebService"


class DaolvSpider(Spider):
    source_type = 'daolvApiHotel'
    targets = {
        'Room': {'version': 'InsertNewRoom'},
        # 'verifyRoom': {'version': 'InsertNewRoom'}
    }
    old_spider_tag = {
        'daolvApiHotel': {'required': ['Room']}
    }

    def __init__(self, task=None):
        Spider.__init__(self, task=task)
        self.room_obj_list = list()  # 用于存放所有的search返回的room
        self.verify_room = list()  # 用于存放需要验证时，满足房型条件的房间对象

    def targets_request(self):
        @request(user_retry_count=1, proxy_type=PROXY_API, binding=self.parse_Room)
        def search_room():
            request_xml, url = self.process_search_data()
            req_info = {
                'req': {
                    'url': url + '/api/rate/pricesearch',
                    'method': 'post',
                    'data': request_xml
                }
            }
            # use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi', record_tuple=1,
            #                code=1, error_id=0,
            #                api_info=req_info['req'], msg='', httpcode=0, resp='')
            return req_info

        @request(retry_count=3, proxy_type=PROXY_API, binding=self.parse_verifyRoom)
        def verify_room():
            request_list, url = self.process_verify_data()
            for request_xml in request_list:
                return {
                    'req': {
                        'url': url,
                        'method': 'post',
                        'data': request_xml,
                    }
                }

        yield search_room

        # if self.task.ticket_info.get('verify_room', []) != []:
        #     yield verify_room

    def parse_verifyRoom(self, req, resp):
        """
        解析verify请求回的房间信息
        :param req:
        :param resp:
        :return:
        """
        room_list = self.parse_room_util(req, resp)
        return room_list

    def parse_Room(self, req, resp):
        """
        解析search请求回的房间信息
        :param req:
        :param resp:
        :return:
        """
        room_list = self.parse_room_util(req, resp)
        return room_list

    def parse_room_util(self, req, resp):
        """
        解析方法的工具方法，用于parse_Room和parse_verifyRoom
        :return:
        """
        if "Invalid Auth" in resp:
            if json.loads(self.task.ticket_info['auth']).get('apienv', 'test') == 'online':
                use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi',
                               record_tuple=1,
                               error_id=122,
                               api_info={}, msg='', httpcode=req['resp'].status_code, resp='', is_success=1)
            raise parser_except.ParserException(122, '认证信息失败')
        if "Location not found for given descriptor and type" in resp:
            if json.loads(self.task.ticket_info['auth']).get('apienv', 'test') == 'online':
                use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi',
                               record_tuple=1,
                               error_id=99,
                               api_info={}, msg='', httpcode=req['resp'].status_code, resp='', is_success=1)
            raise parser_except.ParserException(99, 'Location not found for given descriptor and type')
        request_info = self.task_parser()
        task = self.task
        redis_key = request_info['redis_key']
        result = []
        try:
            doc = etree.XML(resp)
            RatePlans = doc.xpath('.//RatePlan')
            hotel_name = self.get_first_str(doc.xpath('.//Hotel/HotelName/text()'))
            hotel_id = self.get_first_str(doc.xpath('.//Hotel/HotelID/text()'))
            CityID = str(self.get_first_str(doc.xpath('.//Hotel/Destination/@CityCode')))
            for offer_count, each in enumerate(RatePlans):
                try:
                    room = Room()
                    room.hotel_name = hotel_name
                    room.city = request_info.get('city')
                    room.source = 'daolvApi'
                    room.source_hotelid = hotel_id
                    room.real_source = room.source
                    room.room_type = self.get_first_str(each.xpath('./RatePlanName/text()'))
                    room.occupancy = int(self.get_first_str(each.xpath('./MaxOccupancy/text()')))
                    bed_type = self.get_first_str(each.xpath('./BedType/text()'))
                    """
                    返回的信息中给出的是一个床型id，需要在api中查询具体的信息，因为更新频率低，写成了dict信息存放，更新时
                    更新同目录下的bed_type_json.py即可
                    """
                    bed_type = bed_type_dict.get(str(bed_type), '暂时没有对应信息')
                    if isinstance(bed_type, list):
                        room.bed_type = '{0}; {1}'.format(bed_type[0], bed_type[1])
                    else:
                        room.bed_type = bed_type
                    room.check_in = request_info.get('CheckInDate')
                    room.check_out = request_info.get('CheckOutDate')
                    try:
                        room.rest = int(self.get_first_str(each.xpath('./InventoryCount/text()')))
                    except Exception as e:
                        room.rest = len(self.task.ticket_info['room_info'])
                    room.price = float(self.get_first_str(each.xpath('./TotalPrice/text()')))
                    room.currency = each.find('Currency').text
                    room.has_breakfast = self.has_breakfast(self.get_first_str(each.xpath('./BreakfastType/text()')))
                    room.is_breakfast_free = room.has_breakfast
                    return_rule = each.xpath('./RatePlanCancellationPolicyList/CancellationPolicy')
                    room.return_rule = self.return_rule_str(return_rule)
                    if room.return_rule == 'NULL':
                        room.is_cancel_free = 'No'
                        room.return_rule = ''

                    room.others_info = json.dumps({
                        "rate_key": self.get_first_str(each.xpath('./RatePlanID/text()')),
                        "room_num": len(self.task.ticket_info["room_info"]),
                        "payment_info": "",
                        "rating": "",
                        "payKey": {
                            "redis_key": redis_key,
                            "uid": getuid(),
                            "id": offer_count,
                        },
                        'extra': {
                            'breakfast': self.get_first_str(each.xpath("./BreakfastType/text()")),
                            'payment': '',
                            'size_info': '',
                            'return_rule': room.return_rule,
                            'occ_des': str(room.occupancy),
                            'occ_num': {
                                'adult_num': room.occupancy,
                                'child_num': 0,
                            },
                            'size_info_extra': 0
                        }
                    })

                    room.pay_method = 'mioji'
                    self.room_obj_list.append(room)
                    room_tuple = (room.hotel_name, room.city, room.source, room.source_hotelid, room.source_roomid,
                                  room.real_source, room.room_type, room.occupancy, room.bed_type, room.size,
                                  room.floor,
                                  room.check_in, room.check_out, room.rest, room.price, room.tax, room.currency,
                                  room.pay_method, room.is_extrabed, room.is_extrabed_free, room.has_breakfast,
                                  room.is_breakfast_free, room.is_cancel_free, room.room_desc, room.return_rule,
                                  room.extrabed_rule, room.change_rule, room.others_info, room.guest_info)
                    result.append(room_tuple)
                except Exception as e:
                    logger.error('field not comple %s\n', str(e))
                    raise parser_except.ParserException(ErrNumber.E_UNKNOWN, str(e))
        except Exception as e:
            if json.loads(self.task.ticket_info['auth']).get('apienv', 'test') == 'online':
                use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi',
                               record_tuple=1,
                               error_id=25,
                               api_info={}, msg='', httpcode=req['resp'].status_code, resp='', is_success=0)
            raise parser_except.ParserException(ErrNumber.E_UNKNOWN, str(e))

        if result == []:
            if json.loads(self.task.ticket_info['auth']).get('apienv', 'test') == 'online':
                use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi',
                               record_tuple=1,
                               error_id=291,
                               api_info={}, msg='', httpcode=req['resp'].status_code, resp='', is_success=0)
            raise parser_except.ParserException(291, '无房')
        elif result != []:
            if json.loads(self.task.ticket_info['auth']).get('apienv', 'test') == 'online':
                use_record_api(task=self.task, api_name='PriceSearchRequest', unionkey='daolvApi',
                               record_tuple=1,
                               error_id=0,
                               api_info={}, msg='', httpcode=req['resp'].status_code, resp='', is_success=0)
        return result

    def return_rule_str(self, xmlrule):
        """

        :param xmlrule:
        :return:
        """
        if not xmlrule:
            return 'NULL'
        rules = []
        result = list()
        for each in xmlrule:
            onerule = {}
            onerule['FromDate'] = self.utc_to_local(self.get_first_str(each.xpath('./FromDate/text()')))
            onerule['Amount'] = self.get_first_str(each.xpath('./Amount/text()'))
            rules.append(onerule)
        if len(rules) == 0:
            return 'NULL'
        today = int(self.utc_to_local(datetime.date.today().strftime("%Y-%m-%d")))
        for index, rule in enumerate(rules):
            if index == 0 and index != len(rules) - 1 and int(rule['FromDate']) - today > 0:
                result.append(dict(
                    starttime=today,
                    # datetime=today,
                    endtime=int(rule['FromDate']),
                    charge=0,
                    # currency="CNY",
                    ccy="CNY",
                    desc=""
                ))
                result.append(dict(
                    starttime=int(rule['FromDate']),
                    endtime=int(rules[index + 1]['FromDate']),
                    # datetime=int(rule['FromDate']),
                    charge=float(rule['Amount']),
                    # currency="CNY",
                    ccy="CNY",
                    desc=""
                ))
            elif index == len(rules) - 1:
                result.append(dict(
                    starttime=int(rule['FromDate']),
                    endtime=int(self.utc_to_local(self.check_in)),
                    # datetime=int(rule['FromDate']),
                    charge=float(rule['Amount']),
                    # currency="CNY",
                    ccy="CNY",
                    desc=""
                ))
            else:
                result.append(dict(
                    starttime=int(rule['FromDate']),
                    endtime=int(rules[index + 1]['FromDate']),
                    # datetime=int(rule['FromDate']),
                    charge=float(rule['Amount']),
                    # currency="CNY",
                    ccy="CNY",
                    desc=""
                ))

        # '取消订单开始时间：<FromDate><br/>退单费用：<Amount>元<br/><br/>'
        return json.dumps(result)

    def utc_to_local(self, utc_time_str, utc_format='%Y-%m-%d %H:%M:%S'):
        utc_time = utc_time_str.split("T")[0] + " 00:00:00"
        return time.mktime(time.strptime(utc_time, utc_format))

    def has_breakfast(self, onestr):
        """
        是否有早餐
        :param onestr: 1：没有，2:有
        :return: str
        """
        if int(onestr) == 1:
            return 'No'
        else:
            return 'Yes'

    def get_first_str(self, onelist):
        """
        取xpath取出的list的第一个。避免异常
        :param onelist: xpath取出的list
        :return: list的第一个字符串
        """
        if len(onelist) > 0:
            return onelist[0]
        else:
            return ''

    def process_verify_data(self):
        """
        构造verify的请求数据
        :return:
        """
        request_list = list()
        url, client_id, license_key, child_age_detail, request_info = self.process_data()
        details = ''
        for i in range(1, int(self.task.ticket_info['room_info'][0]['room_num']) + 1):
            ages = ''
            for child in self.task.ticket_info['room_info'][0]['child_info']:
                ages += '<ChildAge>{age}</ChildAge>'.format(age=child)
            details += """
                <RoomOccupancy RoomNum="{i}" AdultCount="{Adult}" ChildCount="{Children}">
                    <ChildAgeDetails>
                        {ages}
                    </ChildAgeDetails>
                </RoomOccupancy>
            """.format(i=i, ages=ages, **request_info)
        for room in self.verify_room:
            verify_RatePlanID = json.loads(room.others_info)['rate_key']
            request_xml = """
                <PriceConfirmRequest>
                    <Header>
                        <ClientID>{client_id}</ClientID>
                        <LicenseKey>{license_key}</LicenseKey>
                    </Header>
                    <HotelID>{HotelID}</HotelID>
                    <RatePlanID>{verify_RatePlanID}</RatePlanID>
                    <CheckInDate>{CheckInDate}</CheckInDate>
                    <CheckOutDate>{CheckOutDate}</CheckOutDate>
                    <NumOfRooms>{RoomCount}</NumOfRooms>
                    <OccupancyDetails>
                        {details}
                    </OccupancyDetails>
                    <PreBook>true</PreBook>
                </PriceConfirmRequest>
            """.format(client_id=client_id, license_key=license_key, details=details,
                       verify_RatePlanID=verify_RatePlanID, **request_info)
            request_list.append(request_xml)
        return request_list, url

    def process_search_data(self):
        """
        构造search的请求数据
        :return:
        """
        url, client_id, license_key, child_age_detail, request_info = self.process_data()
        request_xml = """
                                <PriceSearchRequest>
                                    <Header>
                                        <ClientID>{ClientID}</ClientID>
                                        <LicenseKey>{LicenseKey}</LicenseKey>
                                    </Header>
                                    <HotelIDList>
                                        <HotelID>{HotelID}</HotelID>
                                    </HotelIDList>
                                    <CheckInDate>{CheckInDate}</CheckInDate>
                                    <CheckOutDate>{CheckOutDate}</CheckOutDate>
                                    <IsRealTime RoomCount="{RoomCount}">true</IsRealTime>
                                    <RealTimeOccupancy AdultCount="{Adult}" ChildCount="{Children}">
                                    {child_age_detail}
                                    </RealTimeOccupancy>
                                </PriceSearchRequest>
                                """.format(ClientID=client_id, LicenseKey=license_key,
                                           child_age_detail=child_age_detail,
                                           **request_info)
        return request_xml, url

    def process_data(self):
        """
        构造post请求数据的工具方法
        :param verify_RatePlanID: 便于代码复用，用于search和verify的post数据
        :return:
        """
        request_info = self.task_parser()
        auth = request_info['auth']
        env_name = request_info.get('env_name')
        if not auth.get('ClientID', None) or not auth.get('LicenseKey', None):
            raise Exception(121, '认证信息缺少字段')

        if env_name == 'online':
            # todo online url
            url = auth.get('url', TEST_API_URL)
        else:
            url = auth.get('url', TEST_API_URL)
        children_age = request_info['ChildrenAge']
        if len(children_age) > 0:
            age_list = list()

            for age in children_age:
                age_list.append("<ChildAge>{age}</ChildAge>".format(age=age))
            child_age_detail = "<ChildAgeDetails>" + "".join(age_list) + "</ChildAgeDetails>"
        else:
            child_age_detail = ""
        client_id = auth['ClientID']
        license_key = auth['LicenseKey']
        return url, client_id, license_key, child_age_detail, request_info

    def task_parser(self):
        """
        接受任务,并解析,处理异常
        :return:
        """
        task = self.task
        try:
            contentlist = self.split_content(task.content)
            mj_city_id, hotel_id = contentlist[:2]
            days = int(contentlist[2])
            checkin = datetime.datetime.strptime(contentlist[-1], "%Y%m%d")
            checkout = checkin + datetime.timedelta(days=days)
            checkin_str = checkin.strftime("%Y-%m-%d")
            checkout_str = checkout.strftime("%Y-%m-%d")
            self.check_in = checkin_str
            ticket_info = task.ticket_info
            env_name = ticket_info.get("env_name")
            try:
                room_info = self.get_room_info(checkin_str)
                child_age = [age for age in room_info[0]['child_info'] if age < 18]
                adult = len(room_info[0]['adult_info']) + len([age for age in room_info[0]['child_info'] if age >= 18])
                child = len(child_age)
                self.user_datas['adult_num'] = adult
                self.user_datas['child_num'] = child
                room_count = len(room_info)
            except Exception as e:
                raise parser_except.ParserException(12, '任务错误')
        except Exception as e:
            raise parser_except.ParserException(ErrNumber.E__TASK, str(e))
        redis_key = 'Null'
        if hasattr(task, 'redis_key'):
            redis_key = task.redis_key

        try:
            auth = json.loads(task.ticket_info["auth"])
        # except parser_except.ParserException:
        except Exception:
            raise parser_except.ParserException(121, msg='API认证信息错误')
        request_info = dict(HotelID=hotel_id, CheckInDate=checkin_str, CheckOutDate=checkout_str,
                            city=mj_city_id,
                            RoomCount=room_count, Adult=adult, Children=child, ChildrenAge=child_age, Nationality='CN',
                            env_name=env_name, redis_key=redis_key, auth=auth)
        return request_info

    def split_content(self, content):
        """
        切割输入数据，抛出异常
        :param content:
        :return: contentlist 切割后的list
        """
        try:
            contentlist = content.split('&')
            if len(contentlist) != 4:
                raise Exception(ErrNumber.E__TASK, 'Content split by & not equal to four,task is wrong!')
            if not (contentlist[0] and contentlist[1] and contentlist[2] and contentlist[3]):
                raise Exception(ErrNumber.E__TASK, 'Content split by & has null ,task is wrong!')
            try:
                temptime = time.strptime(contentlist[3], "%Y%m%d")
            except Exception as e:
                raise Exception(ErrNumber.E__TASK, e)
        except Exception as e:
            raise Exception(ErrNumber.E__TASK, str(e))
        return contentlist

    @staticmethod
    def calculate_age(departure_date, born):
        """
        计算年龄，入住日期-出生日期
        :param departure_date:
        :param born:
        :return:
        """
        born = datetime.datetime.strptime(born, '%Y%m%d')
        today = datetime.datetime.strptime(departure_date, '%Y-%m-%d').date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def get_room_info(self, checkin):
        """
        兼容新版age_info和room_info
        :return:
        """
        room_info = list()
        if self.task.ticket_info.get('age_info'):
            for index, room in enumerate(self.task.ticket_info.get('age_info', [])):
                adult_info = []
                child_info = []
                for people in room:
                    age = self.calculate_age(checkin, people)
                    if age < 18:
                        child_info.append(age)
                    else:
                        adult_info.append(age)
                room_info.append(dict(
                    adult_info=adult_info,
                    child_info=child_info
                ))
        else:
            room_info = self.task.ticket_info.get('room_info', [])
        # 判断每间房人员类型是否相同，不同就报错
        for index, room in enumerate(room_info):
            if index == 0:
                continue
            if len(room['adult_info']) != len(room_info[index - 1]['adult_info']):
                raise parser_except.ParserException(12, "房间类型不同")
            if len(room['child_info']) != len(room_info[index - 1]['child_info']):
                raise parser_except.ParserException(12, "房间类型不同")
        return room_info

    def response_error(self, req, resp, error):
        if resp.status_code == 400:
            import re
            try:
                message = re.search(r'<Message>(.*)</Message>', resp.text).group(1)
            except Exception:
                message = ""
            raise parser_except.ParserException(29, message)
        raise parser_except.ParserException(89, "服务出错啦啊啊～～！http code: {}".format(req['resp'].status_code))


def utc_to_local(utc_time_str="2019-01-11", utc_format='%Y-%m-%d %H:%M:%S'):
    utc_time = utc_time_str.split("T")[0] + " 00:00:00"
    return time.mktime(time.strptime(utc_time, utc_format))


if __name__ == '__main__':
    task = Task()
    task.source = 'daolv hotel'
    auth = json.dumps({"acc_mj_uid": "daolv_001", "ClientID": "Mioji", "LicenseKey": "Mioji",
            "url": "http://api.didatravel.com", "apienv": "test"})
    # auth = json.dumps(auth)
    # task.ticket_info = {'env_name': 'test', "room_info": {"num": 2, "occ": 2}, "auth": auth, 'room_count': 1}
    # task.ticket_info = {
    #     'env_name': 'test',
    #     'room_info': [{"adult_info": [33, 44], "child_info": [9, 5]}],
    #     "auth": auth,
    #     'room_count': 1,
    #     # "verify_room": ["DOUBLE CITY VIEW TWO QUEEN BEDS"]
    # }
    task.redis_key = 'asdfasdfasdf'
    # 测试数据，美国 加州 奥克兰 滨水杰德微精品酒店
    # task.content = '13000&28333&3&20170809'
    # task.content = '13000&28333&3&20180610'
    # task.content = "30095&64958&1&20180905"

    for content in ['20977&39773&1&20190531', '20150&18131&2&20190508', '20070&3965&2&20190510',
                    'NULL&218279&3&20190531']:
        task.content = content
        task.ticket_info = {
            "room_info": [{"adult_info": [24], "child_info": [5]}, {"adult_info": [24], "child_info": [5]}],
            "auth": auth,
            "age_info": [["19960815", "20060815"]]
        }

        spider = DaolvSpider()
        spider.task = task
        spider.crawl()
        for x in spider.result["Room"]:
            print(x[-5])
            print("*" * 100)
