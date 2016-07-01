#### supervisor配置:

* * *

* 将web-server.conf文件放置于/etc/supervisor/conf.d/ 目录下

* 运行如下命令可以监控和启动web

    * $ sudo supervisorctl reload
    
    * $ sudo supervisorctl start web-server
    
    * $ sudo supervisorctl status 


* 需要注意的地方：
    
    * app.py文件必须可执行，所以需要在python中引入/usr/bin/env python3, 然后为文件添加x权限

    * supervisor只负责运行app.py，服务器相关配置需要Nginx配置
    




