# -*- coding:utf-8 -*-

__author__ = "Parle"

import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError


'''
get和postz装饰器为handle函数对象加上路径和方法名称属性
'''
# 将一个函数包装起来，映射称为URL处理函数，使其附带URL信息
def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)    # 保持函数名不变
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'GET'
        wrapper.__route__  = path
        return wrapper
    return decorator

def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'POST'
        wrapper.__route__  = path
        return wrapper
    return decorator



'''
# 关于inspect.Parameter 的  kind 类型有5种：
# POSITIONAL_ONLY        只能是位置参数
# POSITIONAL_OR_KEYWORD  可以是位置参数也可以是关键字参数
# VAR_POSITIONAL         相当于是 *args
# KEYWORD_ONLY           关键字参数且提供了key，相当于是 *,key
# VAR_KEYWORD            相当于是 **kw
'''

# 获取需要传入值的命名关键字参数
def get_required_kw_args(fn):
    args=[]
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # 找到没有默认值的命名关键字参数
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            print(name)
            args.append(name)
    return tuple(args)


# 获取命名关键字参数
def get_named_kw_args(fn):
    args=[]
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # 找到没有默认值的命名关键字参数
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


# 判断keywords 参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # 参数的类型不是可变参数，关键字参数或者命名关键字参数
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s)' %(fn.__name__, str(sig)))
    return found


# 封装URL处理函数，解析这些函数所需要传入的参数(反射)
# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数,然后将结果转换为response
class RequestHandler(object):
    def __init__(self, app, fn):
        self._app = app
        # URL处理函数
        self._func = fn
        # 分析函数参数
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)
        self._has_named_kw_arg = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    @asyncio.coroutine
    def __call__(self, request):    
        # aiohttp的request可以使用web模块进行构造，不需要人工构造

        kw = None
        logging.info(' %s : has_request_arg = %s,  has_var_kw_arg = %s, has_named_kw_args = %s, get_named_kw_args = %s, get_required_kw_args = %s ' 
            % (__name__, self._has_request_arg, self._has_var_kw_arg, self._has_named_kw_arg,self._named_kw_args ,self._required_kw_args))
        
        if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type')
                # aiohttp支持json或者www-form-urlencoded数据传输格式的解析
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('application/form-data'):
                    params = yield from request.post()
                    kw = dict(**arams)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' %request.content_type)
            
            if request.method == 'GET':
                # url中的请求子串,eg: id=1
                qs = request.query_string
                logging.info('qs = %s' %qs)
                if qs:
                    kw = dict()
                    for k ,v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]

        # 一些只读属性
        if kw is None:
            kw = dict(**request.match_info)
            logging.info('kw = %s' %kw)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:                
                # remove all unamed kw
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy

                # check named arg
                for k, v in request.match_info.items():
                    if k in kw:
                        logging.warning('Duplicate arg name in named arg and kw args: %s ' %k)
                    kw[k] = v

        # 
        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' %str(kw))

        try:
            r = yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)  


def add_static(app):
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static: %s => %s' %('/static/', path))


def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)

    if path is None or method is None :
        raise ValurError('@get or @post not defined in %s.' %str(fn))

    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    
    logging.info('add route: %s %s => %s(%s)' %(method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    n = module_name.rfind(".")
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)

    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)

        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)





    
