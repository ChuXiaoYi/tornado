# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/19 下午4:28
#       @Author  : cxy =.= 
#       @File    : TokenBucket.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import time
import asyncio
class Token(object):
    def __init__(self):
        self.token = int(time.time())

class TokenBucket(object):
    def __init__(self, conf):
        """

        :param rate: 1/qps
        :param capacity: 桶的容量   每个请求最多等待30s，用qps*30就是桶的最大容量
        :param _capacity_list: 桶中的token列表
        """
        self._rate = 3/5
        self._capacity = (5/3) * 30
        self._capacity_list = list()
        self._first = int(time.time())

    def produce(self):
        """
        生产token
        :return:
        """
        token = Token()
        if len(self._capacity_list) == self._capacity:
            return False
        print(f'放入了{token}')
        self._capacity_list.append(token)
        return token


    def consume(self, token):
        """

        :return:
        """
        while True:
            time_now = int(time.time())
            if time_now - self._first >= self._rate and self._capacity_list[0] == token:
                print(f'当前bucket中的token: {self._capacity_list}')
                print(f'完成的token: {token}，上一次操作的时间：{self._first}, 当前操作时间：{time_now}该token等待时间：{time_now - self._first}')
                self._capacity_list.pop(0)
                self._first = time_now
                return token




if __name__ == '__main__':
    bucket = TokenBucket()

    while True:
        now = time.time()
        bucket.consume(now)


