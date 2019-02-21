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
