#### Nginx配置:

* * *

* 安装Nginx
 
* 将web-server文件放置于/etc/nginx/sites-available/ 目录下

* 在/etc/nginx/sites-enable/ 目录下创建软链接

    * $ sudo ln -s /etc/nginx/sites-available/web-server .


* 重新加载Nginx服务

    * $ sudo /etc/init.d/nginx reload  