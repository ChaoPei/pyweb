# -*- coding:utf-8 -*-

__auth__ = 'Parle'

'''
web建立在asyncio的基础上
用aiohttp写一个基本的web frame 
'''

import logging;logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time

from datetime import datetime

from aiohttp import web

from jinja2 import Environment, FileSystemLoader

import orm

from coroweb import add_routes, add_static

from handlers import cookie2user, COOKIE_NAME


def init_jiaja2(app, **kw):
    logging.info('init jinja2...')
    # 初始化模板配置，包括模板运行代码的标志符
    options = dict(
            autoescape = kw.get('autoescape', True),
            block_start_string = kw.get('block_start_string', '{%'),
            block_end_string = kw.get('block_end_string', '%}'),
            variable_start_string = kw.get('variable_start_string', '{{'),
            variable_end_string = kw.get('variable_end_string', '}}'),
            auto_reload = kw.get('auto_reload', True)
            )

    path = kw.get('path', None)

    # add templates path
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 temaplate path: %s' % path)
    env = Environment(loader = FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


# URL处理：记录URL日志
@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):        # aiohttp.web create the request automatically
        logging.info('Request: %s %s' %(request.method, request.path))

        # wait for handler
        # handler can be any callable that accepts a Request instance(only)
        return (yield from handler(request))
    return logger


# URL处理：取出POST中的数据
@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s' %str(request__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s' %str(request.__data__))
        return (yield from handler(request))

    return parse_data



# 对url请求中的manage进行拦截，检查是否为管理员
@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth



'''
#响应处理
#总结下来一个请求在服务端收到后的方法调用顺序是:
#       logger_factory->response_factory->RequestHandler().__call__->get或post->handler
#那么结果处理的情况就是:
#       由handler构造出要返回的具体对象
#       然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象并使接下来的程序容易处理
#       RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数,然后把结果返回给response_factory
#       response_factory在拿到经过处理后的对象，经过一系列对象类型和格式的判断，构造出正确web.Response对象，以正确的方式返回给客户端
#在这个过程中，我们只用关心我们的handler的处理就好了，其他的都走统一的通道，如果需要差异化处理，就在通道中选择适合的地方添加处理代码
'''
# URL处理：将返回值转换为Response对象再返回,便于aiohttp处理
@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler: %s' %(handler.__name__))
        r = yield from handler(request)     # handle request and return result r
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octest-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >=100 and t < 600:
                return web.Response(t, str(m))

        #default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = "text/plain;charset=utf-8"
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() -t)
    if delta < 60:
        return u'1 min ago'
    if delta < 3600:
        return u'%s mins ago' %(delta // 60)
    if delta < 86400:
        return u'%s hours ago' %(delta // 3600)
    if delta < 604800:
        return u'%s days ago' %(delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' %(dt.year, dt.month, dt.day)



#event_loop的init也是一个coroutine
@asyncio.coroutine
def init(loop):
    # init connection pool
    yield from orm.create_pool(loop = loop, user='web', port=3306, password='webadmin',db='web')

	# 实例化一个web Application
    app = web.Application(loop=loop, middlewares=[logger_factory, auth_factory, response_factory])

    init_jiaja2(app, filters=dict(datetime=datetime_filter))
    
    
    # 设置请求路径(url地址)及其响应
    add_routes(app, 'handlers')
    add_static(app)
    
    
    # 为每一个请求建立一个协程连接
    srv = yield from loop.create_server(app.make_handler(),'127.0.0.1', 9000)
    logging.info('Server start at http://127.0.0.1:9000...')
    print('Server start at http://127.0.0.1:9000...\n\n\n')
    return srv
 
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()

