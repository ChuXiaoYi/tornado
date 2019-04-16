# -*- coding: utf-8 -*-
# ---------------------------------------------
#       @Time    : 2019/4/16 1:31 PM
#       @Author  : cxy =.= 
#       @File    : httpclient_test.py
#       @Software: PyCharm
#       @Desc    : 
# ---------------------------------------------
from tornado import httpclient


#
# http_client = httpclient.HTTPClient()
# try:
#     response = http_client.fetch("http://www.tornadoweb.org/en/stable/")
#     print(response.body.decode('utf8'))
# except httpclient.HTTPClientError as e:
#     print(f"Error: {str(e)}")
# except Exception as e:
#     print(f"Error: {str(e)}")
# http_client.close()

async def f():
    http_client = httpclient.AsyncHTTPClient()
    try:
        response = await http_client.fetch("http://www.tornadoweb.org/en/stable/")
    except Exception as e:
        print("Error: %s" % e)
    else:
        print(response.body.decode('utf8'))

if __name__ == '__main__':
    import tornado
    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(f)