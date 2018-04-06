# -*- coding: utf-8 -*-

from threading import Thread
import functools
import time
import logging

def timeout(timeout):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (func.__name__, timeout))]
            def newFunc():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception, e:
                    res[0] = e
            t = Thread(target=newFunc)
            t.daemon = True
            try:
                t.start()
                t.join(timeout)
            except Exception, je:
                logging.info('error when starting thread')
                raise je
            ret = res[0]
            if isinstance(ret, BaseException):
                # print 'ret'
                raise ValueError('This function is running too much time. STOP!!!')
            return ret
        return wrapper
    return deco

##Poniżej zastosowanie tej funkcji


# def long_function():
#     while True:
#         print("LEEEEROYYY JENKINSSSSS!!!")
#         time.sleep(10)
#
#
# func = timeout(timeout=25)(long_function)
# try:
#     func()
# except ValueError as err:
#     print(err)