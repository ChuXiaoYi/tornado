# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 12:42 PM
#       @Author  : cxy =.= 
#       @File    : coroutine_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------


async def yield_test():
    yield 1
    yield 2
    yield 3


async def main():
    result = await yield_test()


async def main2():
    await yield_test()
