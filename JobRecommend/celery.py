"""
Celery 配置
"""

import os
from celery import Celery
from django.conf import settings

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'JobRecommend.settings')

# 创建 Celery 实例
app = Celery('JobRecommend')

# 从 Django 设置中加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 配置任务队列
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# 任务超时设置
app.conf.task_time_limit = 60 * 5  # 5分钟硬超时
app.conf.task_soft_time_limit = 60 * 3  # 3分钟软超时

# 任务序列化
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = True
