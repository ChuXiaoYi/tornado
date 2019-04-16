# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 1:45 PM
#       @Author  : cxy =.= 
#       @File    : tornado_spider.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from tornado import gen, httpclient, ioloop, queues

base_url = "http://www.tornadoweb.org/en/stable/"
concurrency = 3


async def get_url_links(url):
    response = await httpclient.AsyncHTTPClient.fetch("http://www.tornadoweb.org/en/stable/")
    html = response.body.decode('utf8')
    soup = BeautifulSoup(html)
    links = [urljoin(base_url, a.get('href')) for a in soup.find_all("a", href=True)]
    return links


async def main():
    seen_set = set()
    q = queues.Queue()

    async def fetch_url(current_url):
        """
        生产者
        :param current_url:
        :return:
        """
        if current_url in seen_set:
            return

        print(f"获取：{current_url}")
        seen_set.add(current_url)
        next_url = await get_url_links(current_url)
        for new_url in next_url:
            if new_url.startswith(base_url):
                await q.put(new_url)

    async def worker():
        async for url in q:
            if url is None:
                return
            try:
                await fetch_url(url)
            except Exception as e:
                print(f'exception')

            finally:
                q.task_done()

    # 放入初始url到队列
    await q.put(base_url)
    # 启动协程
    workers = gen.multi([worker() for i in range(concurrency)])
    await q.join()

    for i in range(concurrency):
        await q.put(None)

    await workers

if __name__ == '__main__':
    ioloop = ioloop.IOLoop.current()
    ioloop.run_sync(main)
