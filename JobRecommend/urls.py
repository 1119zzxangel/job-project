"""JobRecommend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from job import views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('^$', views.login),
    path('login/', views.login, name="login"),  # 登入
    path('register/', views.register, name="register"),  # 注册
    path('logout/', views.logout, name="logout"),  # 登出
    path('index/', views.index, name="index"),  # 主页
    path('welcome/', views.welcome, name="welcome"),
    path('spiders/', views.spiders, name="spiders"),
    path('start_spider/', views.start_spider, name="start_spider"),  # 启动爬虫接口
    path('job_list/', views.job_list, name="job_list"),
    re_path(r'^get_job_list/$', views.get_job_list, name="get_job_list"),
    path('get_psutil/', views.get_psutil, name="get_psutil"),
    path('get_pie/', views.get_pie, name="get_pie"),
    path('send_job/', views.send_job, name="send_job"),  # 投递或取消
    path('job_expect/', views.job_expect, name="job_expect"),  # 求职意向
    path('get_recommend/', views.get_recommend, name="get_recommend"),  # 职位推荐
    path('send_list/', views.send_list, name="send_list"),  # 已投递列表
    path('send_page/', views.send_page, name="send_page"),  # 已投递列表
    path('pass_page/', views.pass_page, name="pass_page"),
    path('up_info/', views.up_info, name="up_info"),  # 修改信息
    path('profile/', views.update_profile, name="update_profile"),  # 更新个人信息（头像/联系方式）
    path('request_reset/', views.request_password_reset, name="request_password_reset"),
    path('reset_password/', views.reset_password, name="reset_password"),
    path('salary/', views.salary, name="salary"),
    path('edu/', views.edu, name="edu"),
    path('bar_page/', views.bar_page, name="bar_page"),
    path('bar/', views.bar, name="bar"),
    path('resume_match/', views.resume_match, name="resume_match"),  # 简历匹配页面
    path('upload_resume/', views.upload_resume, name="upload_resume"),  # 上传简历处理
    path('match_report/', views.match_report, name='match_report'),
    path('download_report_html/', views.download_report_html, name='download_report_html'),
    path('download_report_pdf/', views.download_report_pdf, name='download_report_pdf'),
]
