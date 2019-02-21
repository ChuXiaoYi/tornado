# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/2/21 下午2:48
#       @Author  : cxy =.= 
#       @File    : spider_factory.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
import os
import inspect
import pkgutil
import importlib
import traceback

from mioji.common.spider import Spider

class SpiderFactory(object):
    """
    spider工厂类，用于生产spider

    """
    def __init__(self):
        self.spider_dict = {}

    def load(self):
        """
        在服务开启的时候，加载所有的spider到工厂实例的属性中
        :return:
        """
        print("=====开始初始化spider=====")
        spider_dict = {}

        source_module_names = find_module_names('spider')
        for source in source_module_names:
            print(f"找到source：{source}")
            spider_package = 'spider.' + source

            spider_module_names = find_module_names(spider_package)
            for spider_module in spider_module_names:
                try:
                    print(f"找到module: {spider_module}")
                    if spider_module.endswith('_spider'):
                        desc = init_spider(spider_package + '.' + spider_module)
                        if desc:
                            desc[0]['source_key'] = source
                            spider_dict[desc[0]['source_type']] = desc[0]
                except Exception:
                    print(f"寻找并加载 [ module ]: {spider_module} 时出现异常，[ {traceback.format_exc()} ]")

        self.spider_dict = spider_dict
        print(f'spiders: {self.spider_dict}')
        print('=======spider init complete======')

def init_spider(module_name):
    """
    :param module_name: like  spider.booking.hotel_list_spider
    :return:
    """
    print(module_name)
    spider_module = importlib.import_module('.' + module_name, 'mioji')
    spider_list = []
    for attr in inspect.getmembers(spider_module):
        if inspect.isclass(attr[1]) and attr[1].__module__.endswith('_spider') and attr[1].__module__.endswith(module_name):
            if issubclass(attr[1].__bases__[0], Spider) :
                # 当为 Spider 子类或同类时加载
                try:
                    spider_clazz = getattr(spider_module, attr[0])
                    spider = spider_clazz()
                    if isinstance(spider, Spider):
                        spider_desc = {}
                        spider_desc['source_type'] = spider.source_type
                        spider_desc['spider_class'] = spider_clazz
                        spider_desc['targets'] = spider.targets.keys()
                        spider_list.append(spider_desc)
                except:
                    print(f'instance spider[{attr[1]}]')


    return spider_list



def find_module_names(name):
    p = importlib.import_module('.%s'%name,'mioji')
    c = pkgutil.iter_modules([os.path.dirname(p.__file__)])
    file_list = [name for _, name, _ in c]
    return file_list

if __name__ == '__main__':
    SpiderFactory().load()