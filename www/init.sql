-- init.sql

drop database if exists web;

create database web;

use web;

alter database web character set utf8;

-- add manager user
-- username: web
-- password: admin
grant select, insert, update, delete on web.* to 'web'@'localhost' identified by 'webadmin';

create table users (
	`id` varchar(50) not null,
	`email` varchar(50) not null,
	`passwd` varchar(50) not null,
	`admin` bool not null,
	`name` varchar(50) not null,
	`image` varchar(500) not null,
	`created_at` real not null,
	unique key `idx_email` (`email`),
	key `id_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`name` varchar(50) not null,
	`summary` varchar(200) not null,
	`content` MEDIUMTEXT not null,
	`created_at` real not null,
	key `id_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;


create table comments (
	`id` varchar(50) not null,
	`blog_id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`content` MEDIUMTEXT not null,
	`created_at` real not null,
	key `id_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

