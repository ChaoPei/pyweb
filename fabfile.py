# -*- coding:utf-8-*-

__author__ = 'Pei Chao'

'''
Deployment toolkit
'''

import os, re

from datetime import datetime
from fabric.api import *

env.user = 'peic'
env.sudo_user = 'root'
env.hosts = ['219.223.197.222']

db_user = 'web'
db_password = 'webadmin'

_TAR_FILE = 'dist-web.tar.gz'

_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE

_REMOTE_BASE_DIR = '/srv/web-server'

def _current_path():
    return os.path.abspath('.')

def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M,%S')

def backup():
    '''
    Dump entire database on server and backup to local
    '''
    dt = _now()
    f = 'backup-web-%s.sql' %dt
    with cd('/tmp'):
        run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick web > %s' %(db_user, db_password, f))