# -*- coding:utf8 -*-

__author__ = 'Parle'

'''
url处理函数，处理各种形式的url请求
'''


import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post
from models import User, Comment, Blog, next_id
from config import configs
from apis import APIValueError, APIResourceNotFoundError, Page

from aiohttp import web 
# use markdown implementation
import markdown2

logging.basicConfig(leverl=logging.DEBUG)

COOKIE_NAME = "websession"
_COOKIE_KEY = configs.session.secret

# email 正则表达匹配式
RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# 密码sha1 正则表达匹配式
RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


# 检查当前用户是否是admin
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


# 从字符串中获取页数，有容错处理
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


# 把文本格式转换为html格式
def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


# 根据用户信息生成一个cookie
def user2cookie(user, max_age):
    # build cookie string by: id-expores-shal
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' %(user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


# 从cookie中解析用户信息
@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid
    '''
    if not cookie_str:
        logging.info("cookie_str is null!")
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            logging.info("cookie form is error!")
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            logging.info("expires is error!")
            return None
        
        user = yield from User.find(uid)
        
        if user is None:
            logging.info("user is not exist!")
            return None
        s = "%s-%s-%s-%s" %(uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info("invaild sha1!")
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
        return None


# 首页，默认访问页面，显示博客列表
'''
@get('/')
def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }
'''
@get('/')
def index(*, page='1'):
    # 获取到要展示的博客页数是第几页
    page _index = get_page_index(page)
    # 查找博客表里的条目数
    num = yield from Blog.findNumber('count(id)')
    # 通过Page类来计算当前页的相关信息
    page = Page(num, page_index)
    if num == 0:
        blogs=[]
    else:
        blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))

    # 返回给浏览器
    return {
        '__template__': 'blogs.html'
        'page': page,
        'blogs':blogs
    }


# 注册页面
@get('/register')
def register():
    return {
            '__template__': 'register.html'
        }


# 登录页面
@get('/signin')
def signin():
    return {
            '__template__': 'signin.html'
        }


# 登录认证请求
@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invaild email.')
    if not passwd:
        raise APIValueError('passwd', 'Invaild passwd.')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]

    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid Password.')

    # authenticate ok, set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# 注销
@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-*deleted*-', max_age=0, httponly=True)
    logging.info('user signout out.')
    return r


# 进入某条blog
@get('/blog/{id}')
@asyncio.coroutine
def get_blog(id):
    # 根据博客id查询该博客的信息
    blog = yield from Blog.find(id)
    # 根据博客id查询该条博客的评论
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')

    # 把博客正文和评论套如到markdown2中
    for c in comments:
        c.html_content=text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)

    # 返回页面
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


# 管理页面
@get('/manage/')
def manage():
    return 'redirect:/manage.comments'


# 管理评论页面
@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
            '__template__': 'manage_comments.html',
            'page_index': get_page_index(page)
    }


# 管理用户页面
@get('/manage/users')
def manage_users(*, page='1'):
    return {
            '__template__': 'manage_users.html',
            'page_index':get_page_index(page)
    }


# 管理博客页面
@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index':get_page_index(page)
    }


# 创建博客页面
@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


# 编辑博客页面
@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
            '__template__': 'manage_blog_edit.html',
            'id': id,
            'action': '/api/blog/%s' % id
    }




'''
API数据接口：
    网站对外开放的数据请求接口，直接返回json数据
    admin用户也可以通过api接口直接对blog数据进行修改和创建
    可以通过api进行注册，但暂时未开通对user信息的修改
'''
# 注册请求
@post('/api/users')
@asyncio.coroutine
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not RE_SHA1.match(passwd):
        raise APIValueError('password')

    # 要求邮箱是唯一的
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:faild', 'email', 'Email is already in use')
    
    # 生成当前注册用户唯一的uid
    uid = next_id()
    sha1_passwd = '%s:%s' %(uid, passwd)
    
    # 创建一个用户并保存
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), 
        image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()
    logging.info('save user: %s ok' % name)

    # 构建返回信息
    r = web.Response()
    # 添加cookie
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    # 设置返回的数据格式是json
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# 通过api获取所有blogs数据
@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)


# 通过api获取某条blog数据
@get('/api/blogs/{id}')
@asyncio.coroutine
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog


# 通过api创建blog
@post('/api/blogs')
@asyncio.coroutine
def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()
    return blog


# 通过api更新某条blog
@post('/api/blogs/{id}')
@asyncio.coroutine
def api_update_blog(request, *, name, summary, content):
    check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')

    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()
    return blog


# 通过api删除某条blog 
@post('/api/blogs/{id}/delete')
@asyncio.coroutine
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)


# 通过api获取所有用户信息，保护密码信息
@get('/api/users')
@asyncio.coroutine
def api_get_users():
    users = yield from User.findAll(orderBy='created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users=users)


# 通过api创建评论
@post('/api/blogs/{id}/comments')
@asyncio.
def api_create_comment(id, request, *, content):
    user = request.__user__
    # 必须为登录状态下才能发表评论
    if user is None:
        raise APIPermissionError('content')

    # 评论不能为空
    if not content or not content.strip():
        raise APIValueError('content')

    # 查询bolg id是否存在
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')

    # 创建一条评论
    comment = Comment(blog_id = blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    yield from comment.sava()
    return comment


# 通过api获取评论
@get('/api/comments')
@asyncio.coroutine
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = yield from Comment.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return dict(page=p, comments=comments)


# 通过api删除某条评论
@post('/api/comments/{id}/delete')
@asyncio.coroutine
def api_delete_comments(id, request):
    logging.info(id)
    check_admin(request)
    c = yield from Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)

