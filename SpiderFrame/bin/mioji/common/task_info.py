# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/21 上午11:36
#       @Author  : cxy =.= 
#       @File    : task_info.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import time
import uuid
import json
import datetime

TASK_DATE_FORMAT = '%Y%m%d'

class Task:
    """格式化抓取任务
    """
    def __init__(self, source='demo', content=None, extra={}):
        self.create_time = time.time()              # 任务被初始化的时间
        self.exec_time = None                       # 任务开始执行的时间
        self.new_task_id = str(uuid.uuid1())        # 标识唯一任务
        self.task_type = False                      # 用于表示任务类型，api验证，ota验证，     非api和ota验证任务
        self.content = None
        self.source = None
        self.qid = None
        self.task_id = self.new_task_id
        self.tid = ""
        self.ori_type = ""
        self.ticket_info= dict()
        self.order_no = ""

    def __str__(self):
        return json.dumps(self.__dict__)

class ParseTask(object):
    def __init__(self):
        pass

class RequiredRoom(object):
    __slots__ = ('adult', 'child', 'child_age')

    def __init__(self, value={'adult': 2, 'child': 0, 'child_age': []}, default_child_age=6):
        self.adult = value.get('adult', 2)
        self.child = value.get('child', 0)
        self.child_age = value.get('child_age', [default_child_age] * self.child)

class HotelParams(object):
    __slots__ = ('check_in', 'check_out', 'night', 'rooms_required', 'rooms_count', 'adult', 'child')

    def __init__(self, value={'check_in': '20170512', 'nights': 1, 'rooms': []}):
        self.check_in = datetime.datetime.strptime(value['check_in'], TASK_DATE_FORMAT)
        self.night = value.get('nights', 1)
        self.check_out = self.__init_check_out(self.check_in, self.night)
        self.rooms_count = 0
        self.adult = 0
        self.child = 0
        self.rooms_required = self.__init_rooms_required(value.get('rooms', []))
        self.__init_rooms_info()

    def __init_check_out(self, check_in, nights):
        return check_in + datetime.timedelta(days=nights)

    def __init_rooms_required(self, rooms):
        ps = []
        for r in rooms:
            ps.append(RequiredRoom(value=r))
        if not ps:
            ps.append(RequiredRoom())
        return ps

    def __init_rooms_info(self):
        for r in self.rooms_required:
            self.adult += r.adult
            self.child += r.child
            self.rooms_count += 1

    def format_check_in(self, ft):
        return self.check_in.strftime(ft)

    def format_check_out(self, ft):
        return self.check_out.strftime(ft)