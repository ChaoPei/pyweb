# -*- coding:utf8 -*-

__author__ = 'Parle'

'''
JSON API definition
'''

import json, logging, inspect, functools

class APIError(Exception):
    '''
    The base APIError contains error(required), data(optional) and message(optional)
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.megssage = message


class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The data specifies the error field of input form
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invald', field, message)


class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)


class APIPermissionError(APIError):
    '''
    Indicate the api has no permission
    '''
    def __init__(self, field, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', field, message)



# 页面属性
class Page(object):

    def __init__(self, item_count, page_index=1, page_size=10):
        
        #item_count：要显示的条目数量
        #page_index：要显示的是第几页
        #page_size：每页的条目数量
        '''
        init Pagination by item_count, page_index and page_size
        
        >>> p1 = Page(100, 1)
        >>> p1.page_count
        10
        >>> p1.offset
        0
        >>> p1.limit
        10
        >>> p2 = Page(90, 9, 10)
        >>> p2.page_count
        9
        >>> p2.offset
        80
        >>> p2.limit
        10
        >>> p3 = Page(91, 10, 10)
        >>> p3.page_count
        10
        >>> p3.offset
        90
        >>> p3.limit
        10
        '''

        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        
        # 条目较少，一页足够显示
        if(item_count == 0) or (page_index > self.page_count):
            self.offset = 0;
            self.limit = 0;
            self.page_index = 1
        else:
            # 显示传入的页数
            self.page_index = page_index
            # 计算这个页要显示条目的offset
            self.offset = self.page_size * (page_index - 1)
            # 计算这个页要显示条目数量
            self.limit = self.page_size
        # 是否还有下一页
        self.has_next = self.page_index < self.page_count
        # 是否有上一页
        self.has_previous = self.page_index > 1

        def __str__(self):
            return 'item_count: %s, page_count: %s, page_index:%s, page_size:%s, offset: %s, limit: %s' %(
                self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)
        __repr__ = __str__


