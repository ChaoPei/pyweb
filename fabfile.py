# -*- coding:utf-8-*-

__author__ = 'Pei Chao'

'''
Deployment toolkit
'''

import os, re
from datetime import datetime

# 导入fabric api
from fabric.api import *

# 服务器登录
env.user = 'parle'
env.sudo_user = 'root'
env.hosts = ['219.223.197.222']

# mysql用户名和密码
db_user = 'web'
db_password = 'webadmin'

_TAR_FILE = 'dist-web.tar.gz'

_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE

_REMOTE_BASE_DIR = '/srv/web-server'


# web所在目录(/srv)
def _current_path():
    return os.path.abspath('.')


# 当前日期
def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M,%S')


# 备份任务
def backup():
    '''
    Dump entire database on server and backup to local
    '''
    dt = _now()
    
    # 数据库文件，根据日期进行命名
    f = 'backup-web-%s.sql' %dt
    
    with cd('/tmp'):
        # 备份数据库
        run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick web > %s' %(db_user, db_password, f))
        # 打包压缩
        run('tar -czvf %s.tar.gz %s' %(f, f))
        # 将备份文件从/tmp中转移到相应的位置
        get('%s.tar.gz' %f, '%s/backup/%s.tar.gz' %(_current_path(), f))
        # 删除/tmp中的备份和数据库文件
        run('rm -f %s' % f)
        run('rm -f %s.tar.gz' % f)


# 打包任务，将部署在服务器上的web文件进行打包
def build():
    ''' 
    Build dist package
    '''
    # 包含和排除的目录和文件
    includes = ['static', 'templates', 'favicon.ico', '*.py']
    excludes = ['test', '.*', '*.pyc', '*.pyo']

    # 本地命令
    local('rm -f dist/%s' %_TAR_FILE)

    # 进入www目录
    with lcd(os.path.join(_current_path(), 'www')):    # lcd设定当前命令运行的目录
        # 构建打包命令
        cmd = ['tar', '--dereference', '-czvf', '../dist/%s' %_TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        local(' '.join(cmd))


# 部署任务，将打包后的文件上传至服务器，解压，然后重置www目录的软链接并重启服务
# 软链接以时间来区分命名
def deploy():
    
    # 新的www链接目录命名
    newdir = 'www-%s' %_now()

    # 删除远程服务器缓存的tar文件
    run('rm -f %s' %_REMOTE_TMP_TAR)

    # 上传新的打包文件到远程服务器
    put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)

    # 在远程服务器web-server目录下，创建新的目录
    with cd(_REMOTE_BASE_DIR):
        sudo('mkdir %s' % newdir)
    
    # 解压最新上传的打包文件
    with cd('%s/%s' %(_REMOTE_BASE_DIR, newdir)):
        sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
    
    # 删除旧文件，重置软链接和权限
    with cd(_REMOTE_BASE_DIR):
        sudo("rm -f www")
        sudo('ln -s %s www' % newdir)
        sudo('chown parle:parle www')
        sudo('chown -R parle:parle %s' % newdir)

    # 重启相关服务
    with settings(warn_only = True):
        sudo('supervisorctl stop web')
        sudo('supervisorctl start web')
        sudo('/etc/init.d/nginx reload')

RE_FILES = re.compile('\r?\n')


# 版本回退
def rollback():
    '''
    rollback to previous version
    '''
    with cd(_REMOTE_BASE_DIR):
        
        r = run('ls -p -1')     
        
        # s是列出的某一项，找到存放web文件的文件夹(ls中文件夹以'/'结尾)
        files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]
        files.sort(cmp=lambda s1, s2 : 1 if s1 < s2 else -1)
        
        # 寻找web文件的软链接www
        r = run('ls -l www')
        ss = r.split('->')
        if len(ss) != 2:
            print("ERROR: \www\ is not a symbol link.")
            return
        
        # 查看软链接
        current = ss[1]     # 软链接所指向的文件夹目录
        print('Found current symbol link points to: %s\n' % current)
        try:
            # 在files中查找包含当前软链接的实际文件
            index = files.index(current)
        except ValueError, e:
            print ('ERROR: symbol link is invalid')
            return
        # 最后一项，也就是最老的版本 
        if len(files) == index + 1:
            print('ERROR: already the oldest version')

        old = files[index + 1]
        print('==' * 30)
        for f in files:
            if f == current:
                print('   Current-----> %s' % current)
            elif f == old:
                print('  Rollback to -----> %s' %old)
            else:
                print('              %s' %f)
        print('==' * 30)
        print('')
        yn = raw_input ('continue? y/N')
        if yn != 'y' and yn != 'Y':
            print('Rollback cancelled.')
            return
        print('Start rollback...')

        # 重新建立软链接，设置为上一个版本
        sudo('rm -f www')
        sudo('ln -s %s www' % old)
        sudo('chown parle:parle www')
        with settings(warn_only=True):
            sudo('supervisorctl stop web-server')
            sudo('supervisorctl start web-server')
            sudo('/etc/init.d/nginx reload')
        print('Rollback finished.')


def restore2local():
    '''
    Restore db to local
    '''
    # 备份路径
    backup_dir = os.path.join(_current_path(), 'backup')
    fs = os.listdir(backup_dir)
    # sql备份文件
    files = [f for f in fs if f.startswith('backup-') and f.endswith('.sql.tar.gz')]
    files.sort(cmp=lambda s1, s2:1 if s1 < s2 else -1)

    # 备份文件是否存在
    if len(files) == 0:
        print('No backup files found')
        return 
    print('Found %s backup files:' % len(files))
    print('==' * 30)
    n = 0
    for f in files:
        print('%s: %s' %(n ,f))
        n += 1
    print('==' * 30)
    print('')

    # 选择备份的文件
    try:
        num = int(raw_input('Restore file number:'))
    except ValueError:
        print('Invalid file number')
        return

    restore_file = files[num]
    yn = raw_input('Restore file %s: %s? y/N' %(num, restore_file))
    if yn != 'y' and yn != 'Y':
        print('Restore cancelled.')
        return
    
    # 操作数据库
    print('Start restore to local database...')
    p = raw_input('Input mysql root password:')
    sqls = [
    'drop database if exists web;',
    'create database web;',
    'grant select, insert, update, delete on web.* to \'%s\'@\'localhost\' identified by \'%s\';' 
    %(db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -u root -p %s -e "%s"' %(p, sql))

    # 备份数据库
    with lcd(backup_dir):
        local('tar zxvf %s' % restore_file)
    local(r'mysql -u root -p %s web < backup/%s' %(p, restore_file[:-7]))
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])







