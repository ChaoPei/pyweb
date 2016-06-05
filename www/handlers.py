# -*- coding:utf8 -*-

__author__ = 'Parle'

'''
url handlers
'''


import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

'''
# Test.html
# 因为findAll函数是coroutine修饰的，所以index函数也必须是coroutine修饰
@get('/')
@asyncio.coroutine
def index_test(request):
    users = yield from User.findAll()
    # 将查询结果返回，模版中将调用结果
    return {
            '__template__':'test.html',
            'users':users
        }
 '''   



@get('/')
def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    print('\n\n\n***',blogs,'\n\n\n')
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }
