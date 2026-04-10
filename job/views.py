from django.shortcuts import render, redirect
from django.http import JsonResponse
# Create your views here.
from job import models
import re
import builtins
import json
from psutil import *
import numpy as np
from job import tools
from job import job_recommend
import os
import werkzeug.utils
from job.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from job.utils.resume_parser import parse_file, parse_resume_structured
from job.algorithms.similarity_match import match_resume_to_jobs
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import uuid
from datetime import timedelta
import threading
import time

# 任务状态存储（内存中）
task_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# python manage.py inspectdb > job/models.py
# 使用此命令可以将数据库表导入models生成数据模型


def login(request):
    if request.method == "POST":
        user = request.POST.get('user')
        pass_word = request.POST.get('password')
        print('user------>', user)
        user_obj = models.UserList.objects.filter(user_id=user).first()
        if not user_obj:
            return JsonResponse({'code': 1, 'msg': '该账号不存在！'})
        # 校验哈希密码
        if not check_password(pass_word, user_obj.pass_word or ''):
            return JsonResponse({'code': 1, 'msg': '密码错误！'})
        # 登录成功
        request.session['user_id'] = user
        user_name = user_obj.user_name
        user_role = user_obj.role
        if user_role == 'admin':
            return JsonResponse({'code': 1, 'msg': '管理员请通过 /admin/ 登录！'})
        request.session['user_name'] = user_name
        request.session['user_role'] = user_role
        return JsonResponse({'code': 0, 'msg': '登录成功！', 'user_name': user_name, 'user_role': user_role})
    else:
        return render(request, "login.html")


def register(request):
    if request.method == "POST":
        user = request.POST.get('user')
        pass_word = request.POST.get('password')
        user_name = request.POST.get('user_name')
        users_list = list(models.UserList.objects.all().values("user_id"))
        users_id = [x['user_id'] for x in users_list]
        if user in users_id:
            return JsonResponse({'code': 1, 'msg': '该账号已存在！'})
        else:
            # 存储哈希密码
            models.UserList.objects.create(user_id=user, user_name=user_name, pass_word=make_password(pass_word), role='user')
            request.session['user_id'] = user  # 设置缓存
            request.session['user_name'] = user_name
            request.session['user_role'] = 'user'
            return JsonResponse({'code': 0, 'msg': '注册成功！'})
    else:
        return render(request, "register.html")


# 退出(登出)
def logout(request):
    # 1. 将session中的用户名、昵称删除
    request.session.flush()
    # 2. 重定向到 登录界面
    return redirect('login')


def index(request):
    """此函数用于返回主页，主页包括头部，左侧菜单"""
    return render(request, "index.html")


def welcome(request):
    """此函数用于处理控制台页面"""
    job_data = models.JobData.objects.all().values()  # 查询所有的职位信息
    all_job = len(job_data)  # 职位信息总数
    list_1 = []  # 定义一个空列表
    for job in list(job_data):  # 使用循环处理最高哦薪资
        try:  # 使用try...except检验最高薪资的提取，如果提取不到则加入0
            salary_1 = float(re.findall(r'-(\d+)k', job['salary'])[0])  # 使用正则提取最高薪资
            job['salary_1'] = salary_1  # 添加一个最高薪资
            list_1.append(salary_1)  # 把最高薪资添加到list_1用来计算平均薪资
        except Exception as e:
            # print(e)
            job['salary_1'] = 0
            list_1.append(0)
    job_data = sorted(list(job_data), key=lambda x: x['salary_1'], reverse=True)  # 反向排序所有职位信息的最高薪资
    # print(job_data)
    job_data_10 = job_data[0:10]  # 取最高薪资前10用来渲染top—10表格
    # print(job_data[0:10])
    job_data_1 = job_data[0]  # 取出最高薪资的职位信息
    mean_salary = int(np.mean(list_1))  # 计算平均薪资
    return render(request, "welcome.html", locals())


def model_management(request):
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin':
        return redirect('login')
    
    # 获取所有模型配置
    models = models.ModelConfig.objects.all().order_by('-is_active', '-created_at')
    current_model = models.ModelConfig.objects.filter(is_active=True).first()
    
    return render(request, "modelManage.html", locals())


def add_model(request):
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin' and not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({"code": 1, "msg": "无权限操作"})

    if request.method == "POST":
        model_name = request.POST.get("model_name", "").strip()
        endpoint_id = request.POST.get("endpoint_id", "").strip()
        api_url = request.POST.get("api_url", "").strip()
        model_type = request.POST.get("model_type", "").strip()
        description = request.POST.get("description", "").strip()

        if not model_name:
            return JsonResponse({"code": 1, "msg": "模型名称不能为空"})
        if not endpoint_id:
            return JsonResponse({"code": 1, "msg": "接入点ID不能为空"})
        if not model_type:
            return JsonResponse({"code": 1, "msg": "模型类型不能为空"})

        try:
            # 创建新模型配置
            model_config = models.ModelConfig.objects.create(
                model_name=model_name,
                endpoint_id=endpoint_id,
                api_url=api_url,
                model_type=model_type,
                description=description,
                is_active=False  # 默认不启用，需要手动切换
            )
            return JsonResponse({"code": 0, "msg": f"模型 '{model_name}' 添加成功"})
        except Exception as e:
            return JsonResponse({"code": 1, "msg": f"添加失败：{str(e)}"})
    
    return JsonResponse({"code": 1, "msg": "请求方式错误"})


def switch_model(request):
    """切换当前使用的模型"""
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin' and not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({"code": 1, "msg": "无权限操作"})

    if request.method == "POST":
        model_id = request.POST.get("model_id", "")
        
        if not model_id:
            return JsonResponse({"code": 1, "msg": "模型ID不能为空"})
        
        try:
            # 获取要切换的模型
            target_model = models.ModelConfig.objects.get(model_id=model_id)
            
            # 将所有模型设置为未启用
            models.ModelConfig.objects.all().update(is_active=False)
            
            # 启用目标模型
            target_model.is_active = True
            target_model.save()
            
            # 更新环境变量（当前进程）
            os.environ['DEEPSEEK_ENDPOINT_ID'] = target_model.endpoint_id
            
            return JsonResponse({
                "code": 0, 
                "msg": f"已切换到模型 '{target_model.model_name}'",
                "endpoint_id": target_model.endpoint_id
            })
        except models.ModelConfig.DoesNotExist:
            return JsonResponse({"code": 1, "msg": "模型不存在"})
        except Exception as e:
            return JsonResponse({"code": 1, "msg": f"切换失败：{str(e)}"})
    
    return JsonResponse({"code": 1, "msg": "请求方式错误"})


def update_model(request):
    """更新模型配置（暂不使用）"""
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin' and not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({"code": 1, "msg": "无权限操作"})

    if request.method == "POST":
        model_id = request.POST.get("model_id", "")
        model_name = request.POST.get("model_name", "").strip()
        endpoint_id = request.POST.get("endpoint_id", "").strip()
        model_type = request.POST.get("model_type", "").strip()
        description = request.POST.get("description", "").strip()

        if not model_id:
            return JsonResponse({"code": 1, "msg": "模型ID不能为空"})

        try:
            model_config = models.ModelConfig.objects.get(model_id=model_id)
            if model_name:
                model_config.model_name = model_name
            if endpoint_id:
                model_config.endpoint_id = endpoint_id
            if model_type:
                model_config.model_type = model_type
            if description:
                model_config.description = description
            model_config.save()
            return JsonResponse({"code": 0, "msg": "模型更新成功"})
        except models.ModelConfig.DoesNotExist:
            return JsonResponse({"code": 1, "msg": "模型不存在"})
        except Exception as e:
            return JsonResponse({"code": 1, "msg": f"更新失败：{str(e)}"})

        # 更新模型配置
        # 这里可以根据实际需求实现
        return JsonResponse({"code": 0, "msg": "模型更新成功"})


def delete_model(request):
    """删除模型配置"""
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin' and not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({"code": 1, "msg": "无权限操作"})

    if request.method == "POST":
        model_id = request.POST.get("model_id", "")

        if not model_id:
            return JsonResponse({"code": 1, "msg": "模型ID不能为空"})

        try:
            model_config = models.ModelConfig.objects.get(model_id=model_id)
            model_name = model_config.model_name
            
            # 如果删除的是当前启用的模型，需要清除环境变量
            if model_config.is_active:
                os.environ.pop('DEEPSEEK_ENDPOINT_ID', None)
            
            model_config.delete()
            return JsonResponse({"code": 0, "msg": f"模型 '{model_name}' 删除成功"})
        except models.ModelConfig.DoesNotExist:
            return JsonResponse({"code": 1, "msg": "模型不存在"})
        except Exception as e:
            return JsonResponse({"code": 1, "msg": f"删除失败：{str(e)}"})
    
    return JsonResponse({"code": 1, "msg": "请求方式错误"})



def job_list(request):
    return render(request, "job_list.html", locals())


def get_job_list(request):
    """此函数用来渲染职位信息列表"""
    page = int(request.GET.get("page", ""))  # 获取请求地址中页码
    limit = int(request.GET.get("limit", ""))  # 获取请求地址中的每页数据数量
    keyword = request.GET.get("keyword", "")
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    edu = request.GET.get("edu", "")
    city = request.GET.get("city", "")
    job_data_list = list(models.JobData.objects.filter(name__icontains=keyword, education__icontains=edu,
                                                       place__icontains=city).values())  # 查询所有的职位信息
    job_data = []
    if price_min != "" or price_max != "":
        for job in job_data_list:
            try:
                salary_1 = '薪资' + job['salary']
                max_salary = float(re.findall(r'-(\d+)k', salary_1)[0])  # 使用正则提取最高薪资
                min_salary = float(re.findall(r'薪资(\d+)', salary_1)[0])  # 使用正则提取最低薪资
                if price_min == "" and price_max != "":
                    if max_salary <= float(price_max):
                        job_data.append(job)
                elif price_min != "" and price_max == "":
                    if min_salary >= float(price_min):
                        job_data.append(job)
                else:
                    if min_salary >= float(price_min) and float(price_max) >= max_salary:
                        job_data.append(job)
            except Exception as e:  # 如果筛选不出就跳过
                continue
    else:
        job_data = job_data_list
    job_data_1 = job_data[(page - 1) * limit:limit * page]
    for job in job_data_1:
        ret = models.SendList.objects.filter(user_id=request.session.get("user_id"), job_id=job['job_id']).values()
        if ret:
            job['send_key'] = 1
        else:
            job['send_key'] = 0
    # print(job_data_1)
    if len(job_data) == 0 or len(job_data_list) == 0:
        return JsonResponse(
            {"code": 1, "msg": "没找到需要查询的数据！", "count": "{}".format(len(job_data)), "data": job_data_1})
    return JsonResponse({"code": 0, "msg": "success", "count": "{}".format(len(job_data)), "data": job_data_1})


def get_psutil(request):
    """此函数用于读取cpu使用率和内存占用率"""
    # cpu_percent()可以获取cpu的使用率，参数interval是获取的间隔
    # virtual_memory()[2]可以获取内存的使用率
    return JsonResponse({'cpu_data': cpu_percent(interval=1), 'memory_data': virtual_memory()[2]})


def get_pie(request):
    """此函数用于渲染控制台饼图的数据,要求学历的数据和薪资待遇的数据"""
    edu_list = ['博士', '硕士', '本科', '大专', '不限']
    edu_data = []
    for edu in edu_list:
        edu_count = len(models.JobData.objects.filter(education__icontains=edu))  # 使用for循环，查询字段education包含这些学历的职位信息
        edu_data.append({'name': edu, "value": edu_count})  # 添加到学历的数据列表中
    # print(edu_data)
    list_5 = []
    list_10 = []
    list_15 = []
    list_20 = []
    list_30 = []
    list_50 = []
    list_51 = []
    job_data = models.JobData.objects.all().values()  # 查询所有的职位信息
    for job in list(job_data):
        try:
            salary_1 = float(re.findall(r'-(\d+)k', job['salary'])[0])  # 提取薪资待遇的最高薪资要求
            if salary_1 <= 5:  # 小于5K则加入list_5
                list_5.append(salary_1)
            elif 10 >= salary_1 > 5:  # 在5K和10K之间，加入list_10
                list_10.append(salary_1)
            elif 15 >= salary_1 > 10:  # 10K-15K加入list_15
                list_15.append(salary_1)
            elif 20 >= salary_1 > 15:  # 15K-20K加入list_20
                list_20.append(salary_1)
            elif 30 >= salary_1 > 20:  # 20K-30K 加list_30
                list_30.append(salary_1)
            elif 50 >= salary_1 > 30:  # 30K-50K加入list_50
                list_50.append(salary_1)
            elif salary_1 > 50:  # 大于50K加入list_51
                list_51.append(salary_1)
        except Exception as e:
            job['salary_1'] = 0
    salary_data = [{'name': '5K及以下', 'value': len(list_5)},  # 生成薪资待遇各个阶段的数据字典，value是里面职位信息的数量
                   {'name': '5-10K', 'value': len(list_10)},
                   {'name': '10K-15K', 'value': len(list_15)},
                   {'name': '15K-20K', 'value': len(list_20)},
                   {'name': '20K-30K', 'value': len(list_30)},
                   {'name': '30-50K', 'value': len(list_50)},
                   {'name': '50K以上', 'value': len(list_51)}]
    # print(edu_data)
    return JsonResponse({'edu_data': edu_data, 'salary_data': salary_data})


def send_job(request):
    """此函数用于投递职位和取消投递"""
    if request.method == "POST":
        user_id = request.session.get("user_id")
        job_id = request.POST.get("job_id")
        send_key = request.POST.get("send_key")
        if int(send_key) == 1:
            models.SendList.objects.filter(user_id=user_id, job_id=job_id).delete()
        else:
            models.SendList.objects.create(user_id=user_id, job_id=job_id)
        return JsonResponse({"Code": 0, "msg": "操作成功"})


def job_expect(request):
    if request.method == "POST":
        job_name = request.POST.get("key_word")
        city = request.POST.get("city")
        ret = models.UserExpect.objects.filter(user=request.session.get("user_id"))
        # print(ret)
        if ret:
            ret.update(key_word=job_name, place=city)
        else:
            user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
            models.UserExpect.objects.create(user=user_obj, key_word=job_name, place=city)
        return JsonResponse({"Code": 0, "msg": "操作成功"})
    else:
        ret = models.UserExpect.objects.filter(user=request.session.get("user_id")).values()
        # print(ret)
        if len(ret) != 0:
            keyword = ret[0]['key_word']
            place = ret[0]['place']
        else:
            keyword = ''
            place = ''
        return render(request, "expect.html", locals())


def get_recommend(request):
    recommend_list = job_recommend.recommend_by_item_id(request.session.get("user_id"), 9)
    # 为每个职位添加技能列表
    for job in recommend_list:
        if job.get('required_skills'):
            job['skills_list'] = [skill.strip() for skill in job['required_skills'].split(',') if skill.strip()]
        else:
            job['skills_list'] = []
    # print(recommend_list)
    return render(request, "recommend.html", locals())


def send_page(request):
    return render(request, "send_list.html")


def send_list(request):
    send_list = list(models.JobData.objects.filter(sendlist__user=request.session.get("user_id")).values())
    for send in send_list:
        send['send_key'] = 1
    if len(send_list) == 0:
        return JsonResponse(
            {"code": 1, "msg": "没找到需要查询的数据！", "count": "{}".format(len(send_list)), "data": []})
    else:
        return JsonResponse({"code": 0, "msg": "success", "count": "{}".format(len(send_list)), "data": send_list})


def pass_page(request):
    user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
    return render(request, "pass_page.html", locals())


def up_info(request):
    if request.method == "POST":
        user_name = request.POST.get("user_name")
        old_pass = request.POST.get("old_pass")
        pass_word = request.POST.get("pass_word")
        user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
        if not user_obj:
            return JsonResponse({"Code": 1, "msg": "用户未登录或不存在"})
        if not check_password(old_pass, user_obj.pass_word or ''):
            return JsonResponse({"Code": 1, "msg": "原密码错误"})
        # 更新用户名和密码（密码存储哈希）
        models.UserList.objects.filter(user_id=request.session.get("user_id")).update(user_name=user_name,
                                                                                      pass_word=make_password(pass_word))
        return JsonResponse({"Code": 0, "msg": "密码修改成功"})


def update_profile(request):
    """更新个人信息（头像、联系方式等）"""
    if request.method != 'POST':
        return JsonResponse({"code": 1, "msg": "请使用POST请求"})
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"code": 1, "msg": "未登录"})
    email = request.POST.get('email')
    phone = request.POST.get('phone')
    user_name = request.POST.get('user_name')
    avatar_path = None
    if 'avatar' in request.FILES:
        f = request.FILES['avatar']
        filename = werkzeug.utils.secure_filename(f.name)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(save_path, 'wb') as fh:
            for chunk in f.chunks():
                fh.write(chunk)
        avatar_path = save_path
    update_fields = {}
    if email is not None:
        update_fields['email'] = email
    if phone is not None:
        update_fields['phone'] = phone
    if user_name is not None:
        update_fields['user_name'] = user_name
    if avatar_path:
        update_fields['avatar'] = avatar_path
    if update_fields:
        models.UserList.objects.filter(user_id=user_id).update(**update_fields)
    return JsonResponse({"code": 0, "msg": "更新成功"})


def request_password_reset(request):
    """请求重置密码：生成临时token（示例返回token，真实场景应发邮件）"""
    if request.method != 'POST':
        return JsonResponse({"code": 1, "msg": "请使用POST请求"})
    user_id = request.POST.get('user') or request.POST.get('user_id')
    email = request.POST.get('email')
    user_obj = None
    if user_id:
        user_obj = models.UserList.objects.filter(user_id=user_id).first()
    elif email:
        user_obj = models.UserList.objects.filter(email=email).first()
    if not user_obj:
        return JsonResponse({"code": 1, "msg": "未找到对应用户"})
    token = uuid.uuid4().hex
    expiry = timezone.now() + timedelta(hours=1)
    user_obj.reset_token = token
    user_obj.reset_token_expiry = expiry
    user_obj.save()
    # 在真实环境中应通过邮件发送token；这里直接返回token以便测试
    return JsonResponse({"code": 0, "msg": "重置token已生成", "token": token, "expiry": str(expiry)})


def reset_password(request):
    """使用token重置密码"""
    if request.method != 'POST':
        return JsonResponse({"code": 1, "msg": "请使用POST请求"})
    token = request.POST.get('token')
    new_password = request.POST.get('new_password')
    if not token or not new_password:
        return JsonResponse({"code": 1, "msg": "参数缺失"})
    user_obj = models.UserList.objects.filter(reset_token=token).first()
    if not user_obj:
        return JsonResponse({"code": 1, "msg": "无效的token"})
    if not user_obj.reset_token_expiry or timezone.now() > user_obj.reset_token_expiry:
        return JsonResponse({"code": 1, "msg": "token已过期"})
    user_obj.pass_word = make_password(new_password)
    user_obj.reset_token = None
    user_obj.reset_token_expiry = None
    user_obj.save()
    return JsonResponse({"code": 0, "msg": "密码重置成功"})


def salary(request):
    return render(request, "salary.html")


def edu(request):
    return render(request, "edu.html")


def bar_page(request):
    return render(request, "bar_page.html")


def bar(request):
    key_list = [x['key_word'] for x in list(models.JobData.objects.all().values("key_word"))]
    # print(key_list)
    bar_x = list(set(key_list))
    # print(bar_x)
    bar_y = []
    for x in bar_x:
        bar_y.append(key_list.count(x))
    # print(bar_y)
    return JsonResponse({"Code": 0, "bar_x": bar_x, "bar_y": bar_y})


def resume_match(request):
    """简历匹配页面"""
    return render(request, "resume_match.html")


import requests
import json

def clean_resume_text(text):
    """清洗简历文本，去除冗余内容"""
    import re
    # 移除图片标记
    text = re.sub(r'image\[\[.*?\]\]', '', text)
    # 压缩连续空行
    text = re.sub(r'\n\s*\n', '\n', text)
    # 去除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 限制最大字符数
    return text[:3000]


def extract_resume_by_llm(resume_text):
    """使用火山引擎 DeepSeek V3.2 大模型解析简历，使用HTTP请求"""
    import time
    import os
    import logging
    import random

    logger = logging.getLogger(__name__)
    start_time = time.time()
    max_total_time = 360  # 6分钟超时限制

    # 统一获取 API 配置
    API_KEY = os.getenv("VOLCANO_API_KEY")

    if not API_KEY:
        logger.warning("未设置 VOLCANO_API_KEY 环境变量，使用关键字解析")
        result = parse_resume_structured(resume_text)
        result['parse_method'] = 'keyword'
        result['parse_status'] = 'success'
        return result

    # 从数据库获取当前启用的模型配置
    current_model = None
    try:
        current_model = models.ModelConfig.objects.filter(is_active=True).first()
    except Exception as e:
        logger.error(f"读取模型配置失败：{e}")

    if current_model:
        DEEPSEEK_ENDPOINT_ID = current_model.endpoint_id
        API_URL = current_model.api_url
        logger.info(f"使用数据库配置的模型：{current_model.model_name} ({current_model.model_type})")
    else:
        DEEPSEEK_ENDPOINT_ID = os.getenv("DEEPSEEK_ENDPOINT_ID")
        API_URL = os.getenv("API_URL")
        if not DEEPSEEK_ENDPOINT_ID:
            logger.error("未配置模型，请在模型管理页面添加并启用模型")
            return parse_resume_structured(resume_text)
        if not API_URL:
            logger.error("未配置 API_URL，请在 .env 文件中添加")
            return parse_resume_structured(resume_text)
        logger.info(f"使用环境变量配置的模型：{DEEPSEEK_ENDPOINT_ID}")

    # 检查 API_URL 是否有效
    if not API_URL:
        logger.error("API_URL 为空，使用关键字解析")
        return parse_resume_structured(resume_text)

    logger.debug(f"使用 API URL：{API_URL}")

    # 清洗简历文本
    cleaned_resume = clean_resume_text(resume_text)
    logger.info(f"清洗后简历长度：{len(cleaned_resume)} 字符")

    prompt = """请严格按照以下JSON格式输出，不添加任何其他内容：
{"skills": ["技能1", "技能2"], "education": "最高学历", "experience_year": 工作年限数字, "job_target": "期望岗位"}

从简历中提取：
- skills: 只保留技术技能（编程语言、框架、工具等），去重
- education: 最高学历
- experience_year: 工作年限（数字）
- job_target: 期望岗位

简历：
"""

    full_prompt = prompt + cleaned_resume

    max_retries = 3  # 增加重试次数到3次
    base_timeout = 300  # 增加基础超时时间到300秒

    for attempt in range(max_retries):
        # 检查总时间是否超过6分钟
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_total_time:
            logger.warning(f"大模型解析总时间超过 {max_total_time} 秒，切换到关键字解析")
            result = parse_resume_structured(resume_text)
            result['parse_method'] = 'keyword'
            result['parse_status'] = 'timeout'
            return result

        try:
            # 计算剩余时间并逐步增加超时
            remaining_time = max_total_time - elapsed_time
            timeout_seconds = min(base_timeout + attempt * 60, remaining_time)
            
            logger.info(f"尝试调用大模型 API (尝试 {attempt + 1}/{max_retries})...")
            logger.debug(f"剩余时间: {remaining_time:.0f}秒，本次超时: {timeout_seconds:.0f}秒")

            from openai import OpenAI
            import httpx

            # 完善超时配置
            timeout = httpx.Timeout(
                timeout=timeout_seconds,   # 总超时
                connect=30.0,              # 连接超时
                read=timeout_seconds,      # 读取超时
                write=30.0                 # 写入超时
            )

            client = OpenAI(
                api_key=API_KEY,
                base_url=API_URL,
                timeout=timeout
            )

            logger.debug(f"使用模型: {DEEPSEEK_ENDPOINT_ID}")

            completion = client.chat.completions.create(
                model=DEEPSEEK_ENDPOINT_ID,
                messages=[
                    {"role": "system", "content": "你是一个专业的简历解析助手。"},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )

            logger.info("API 请求成功，正在处理响应...")
            content = completion.choices[0].message.content
            logger.debug(f"API响应内容：{content[:200]}...")

            try:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    parsed = json.loads(json_match.group())
                else:
                    parsed = json.loads(content)

                logger.debug(f"解析结果：{parsed}")

                # 安全转换 experience_year
                experience_year = parsed.get('experience_year', 0)
                try:
                    experience_year = int(experience_year) if experience_year is not None else 0
                except (ValueError, TypeError):
                    experience_year = 0

                result = {
                    "skills": parsed.get('skills', []),
                    "education": parsed.get('education', ''),
                    "total_experience_years": experience_year,
                    "job_target": parsed.get('job_target', '')
                }
                result['parse_method'] = 'llm'
                result['parse_status'] = 'success'
                logger.info("大模型解析成功")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败：{e}")
                break

        except Exception as e:
            logger.error(f"API调用失败：{e}")
            if attempt < max_retries - 1:
                # 指数退避 + 抖动
                backoff_time = min(2 ** attempt * 3, 30)  # 最大等待30秒
                jitter = random.uniform(0, 2)
                total_backoff = backoff_time + jitter
                
                # 检查剩余时间
                elapsed_time = time.time() - start_time
                if elapsed_time + total_backoff >= max_total_time:
                    logger.warning("剩余时间不足，切换到关键字解析")
                    break
                logger.info(f"等待 {total_backoff:.1f} 秒后重试...")
                time.sleep(total_backoff)
                continue
            else:
                break

    logger.info("使用关键字解析方法")
    result = parse_resume_structured(resume_text)
    result['parse_method'] = 'keyword'
    result['parse_status'] = 'fallback'
    return result

def upload_resume(request):
    """处理简历上传和匹配，带超时控制"""
    import time
    start_time = time.time()
    
    if request.method == "POST":
        if 'resume' not in request.FILES:
            return JsonResponse({"code": 1, "msg": "没有找到上传文件"})
        file = request.FILES['resume']
        if file.name == '':
            return JsonResponse({"code": 1, "msg": "未选择文件"})
        if file and allowed_file(file.name):
            filename = werkzeug.utils.secure_filename(file.name)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(save_path, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)
            # 解析文件
            try:
                text = parse_file(save_path)
                print(f"文件解析耗时：{time.time() - start_time:.2f}秒")
            except Exception as e:
                return JsonResponse({"code": 1, "msg": f"解析文件失败：{e}"})

            # 从数据库获取岗位数据
            job_data = list(models.JobData.objects.all().values())
            # 转换岗位数据格式以适配匹配算法
            jobs = []
            for job in job_data:
                # 从职位描述中提取技能点
                description = job.get('name', '') + ' ' + job.get('company', '')
                # 简单提取技能点（实际项目中可能需要更复杂的NLP处理）
                skills = []
                # 这里可以根据实际情况提取技能点
                jobs.append({
                    'id': job.get('job_id'),
                    'title': job.get('name'),
                    'skills': skills,
                    'description': description
                })

            # 执行匹配
            try:
                results = match_resume_to_jobs(text, jobs, top_n=10)
                print(f"匹配算法耗时：{time.time() - start_time:.2f}秒")
            except Exception as e:
                return JsonResponse({"code": 1, "msg": f"匹配失败：{e}"})
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 保存必要信息到 session
            request.session['last_resume_text'] = text
            request.session['last_match_results'] = results
            request.session['last_job_data'] = job_data
            request.session['last_task_id'] = task_id
            
            # 初始化任务状态
            task_status[task_id] = {
                'status': 'processing',
                'result': None,
                'error': None
            }
            
            # 定义后台处理函数
            def process_resume_background():
                try:
                    # 使用大模型解析简历
                    print(f"开始后台处理简历解析...")
                    structured = extract_resume_by_llm(text)
                    print(f"后台解析完成")
                    
                    # 处理匹配结果并计算分项得分
                    enhanced = []
                    # 权重，可配置
                    W_TEXT = 0.7
                    W_STRUCT = 0.3
                    W_SKILLS = 0.6
                    W_EXP = 0.3
                    W_EDU = 0.1

                    # 教育等级映射
                    EDU_RANK = {'不限': 0, '高中': 1, '大专': 2, '本科': 3, '硕士': 4, '博士': 5}

                    for result in results:
                        # 查找对应的岗位信息
                        job_info = next((job for job in job_data if job.get('job_id') == result['id']), {})
                        # 优先使用 required_skills 字段
                        req_skills = []
                        required_skills = job_info.get('required_skills') or ''
                        if required_skills:
                            req_skills = [s.strip() for s in required_skills.split(',') if s.strip()]
                        else:
                            # 回退到 key_word 字段
                            req_skills = [s.lower() for s in (job_info.get('key_word') or '').split() if s.strip()]
                            # 如果岗位没有明确关键词，尝试从jobs结构中使用 skills 字段
                            if not req_skills:
                                # 尝试从职位标签或描述中拆分关键词作为技能
                                key_word_field = job_info.get('key_word') or job_info.get('label') or job_info.get('name') or ''
                                req_skills = [s.lower() for s in re.split(r'[,;\s/\\|]+', key_word_field) if s]

                        resume_skills = [s.lower() for s in structured.get('skills', [])]
                        present = [s for s in req_skills if s.lower() in resume_skills]
                        missing = [s for s in req_skills if s.lower() not in resume_skills]

                        # 技能得分
                        skills_score = 1.0 if not req_skills else (len(present) / len(req_skills))

                        # ==================== 经验得分 ====================
                        job_exp_text = job_info.get('experience') or ''
                        req_years = 0
                        m = re.findall(r"(\d+)", job_exp_text)
                        if m:
                            req_years = int(m[0])

                        resume_years = float(structured.get('total_experience_years', 0) or 0)

                        if req_years == 0:
                            exp_score = 1.0
                        else:
                            try:
                                exp_score = builtins.min(resume_years / float(req_years), 1.0)
                            except Exception:
                                exp_score = 0.0

                        # ==================== 学历得分 ====================
                        job_edu = job_info.get('education') or ''
                        job_edu_rank = 0
                        for k in EDU_RANK:
                            if k != '不限' and k in job_edu:
                                job_edu_rank = EDU_RANK[k]
                                break

                        resume_edu_rank = int(EDU_RANK.get(structured.get('education', '不限'), 0))

                        if job_edu_rank == 0:
                            edu_score = 1.0
                        else:
                            try:
                                edu_score = builtins.min(float(resume_edu_rank) / float(job_edu_rank), 1.0)
                            except Exception:
                                edu_score = 0.0

                        # 结构化部分得分
                        struct_score = W_SKILLS * skills_score + W_EXP * exp_score + W_EDU * edu_score

                        # 文本相似度（来自算法结果）
                        text_sim = float(result.get('score', 0.0))

                        # 综合得分
                        combined = W_TEXT * text_sim + W_STRUCT * struct_score
                        final_score = int(round(combined * 100))

                        enhanced.append({
                            'id': result.get('id'),
                            'title': result.get('title'),
                            'company': job_info.get('company'),
                            'salary': job_info.get('salary'),
                            'place': job_info.get('place'),
                            'score': final_score,
                            'text_similarity': round(text_sim, 4),
                            'skills_score': round(skills_score, 4),
                            'experience_score': round(exp_score, 4),
                            'education_score': round(edu_score, 4),
                            'required_skills': req_skills,
                            'matched_skills': present,
                            'missing_skills': missing,
                        })

                    # 保存到session，便于查看报告与导出
                    request.session['last_resume_structured'] = structured
                    request.session['last_match_enhanced'] = enhanced
                    
                    # 更新任务状态
                    task_status[task_id] = {
                        'status': 'completed',
                        'result': {
                            'results': enhanced,
                            'resume': structured
                        },
                        'error': None
                    }
                except Exception as e:
                    print(f"后台处理失败：{e}")
                    # 更新任务状态
                    task_status[task_id] = {
                        'status': 'failed',
                        'result': None,
                        'error': str(e)
                    }
            
            # 启动后台线程
            thread = threading.Thread(target=process_resume_background)
            thread.daemon = True
            thread.start()
            
            print(f"后台任务已启动，任务ID：{task_id}")
            
            # 返回任务ID给前端
            return JsonResponse({
                "code": 0, 
                "msg": "简历解析任务已提交，请等待处理完成",
                "task_id": task_id
            })
        else:
            return JsonResponse({"code": 1, "msg": f"仅接受以下文件类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"})
    
    else:
        return redirect('resume_match')

def match_report(request, job_id=None):
    """展示匹配报告，包括匹配度最高的前10个岗位。"""
    enhanced = request.session.get('last_match_enhanced') or []
    structured = request.session.get('last_resume_structured') or {}
    if not enhanced:
        return JsonResponse({"code": 1, "msg": "未找到最近的匹配结果，请先上传简历进行匹配。"})
    
    # 按匹配度排序，取前10个
    sorted_enhanced = sorted(enhanced, key=lambda x: x.get('score', 0), reverse=True)[:10]
    
    # 支持通过参数 job_id 指定要展示的岗位详情
    if job_id is None:
        job_id = request.GET.get('job_id')
    target = None
    if job_id:
        for e in enhanced:
            if str(e.get('id')) == str(job_id):
                target = e
                break
    if not target and sorted_enhanced:
        # 默认取第一个（匹配度最高的）
        target = sorted_enhanced[0]

    return render(request, 'match_report.html', {'resume': structured, 'report': target, 'top_jobs': sorted_enhanced})


def download_report_html(request):
    """导出报告为 HTML 文件下载（从 session 读取）"""
    job_id = request.GET.get('job_id')
    enhanced = request.session.get('last_match_enhanced') or []
    structured = request.session.get('last_resume_structured') or {}
    target = None
    for e in enhanced:
        if str(e.get('id')) == str(job_id):
            target = e
            break
    if not target and enhanced:
        target = enhanced[0]
    if not target:
        return JsonResponse({"code": 1, "msg": "未找到报告数据"})

    html = render(request, 'match_report.html', {'resume': structured, 'report': target})
    content = html.content
    filename = f"match_report_{target.get('id')}.html"
    response = JsonResponse({"code": 0, "msg": "生成成功"})
    # 返回原始 html 作为下载
    from django.http import HttpResponse
    resp = HttpResponse(content, content_type='text/html; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


def download_report_pdf(request):
    """尝试使用 weasyprint 将报告导出为 PDF；若不可用则返回错误说明"""
    job_id = request.GET.get('job_id')
    enhanced = request.session.get('last_match_enhanced') or []
    structured = request.session.get('last_resume_structured') or {}
    target = None
    for e in enhanced:
        if str(e.get('id')) == str(job_id):
            target = e
            break
    if not target and enhanced:
        target = enhanced[0]
    if not target:
        return JsonResponse({"code": 1, "msg": "未找到报告数据"})

    # 生成 HTML
    html = render(request, 'match_report.html', {'resume': structured, 'report': target})
    html_content = html.content.decode('utf-8')

    try:
        from weasyprint import HTML
    except Exception:
        return JsonResponse({"code": 1, "msg": "服务器未安装 weasyprint，无法生成 PDF。可先下载 HTML 报告。"})

    pdf = HTML(string=html_content).write_pdf()
    from django.http import HttpResponse
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="match_report_{target.get("id")}.pdf"'
    return resp

# 下面这两段是你原本乱缩进的代码，我帮你正确排版
# 注意：这两个 else 必须有对应的 if，你现在是直接写，会报错！
# 如果你是复制错了，把这两行删掉即可！

# return JsonResponse({"code": 1, "msg": f"仅接受以下文件类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"})
# return redirect('resume_match')

def check_task_status(request):
    """检查任务状态"""
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({"code": 1, "msg": "任务ID不能为空"})
    
    # 获取任务状态
    if task_id not in task_status:
        return JsonResponse({"code": 1, "msg": "任务不存在"})
    
    status_info = task_status[task_id]
    status = status_info['status']
    
    if status == 'completed':
        result = status_info['result']
        return JsonResponse({
            "code": 0, 
            "msg": "任务完成",
            "status": "completed",
            "results": result['results'],
            "resume": result['resume']
        })
    elif status == 'failed':
        error = status_info['error']
        return JsonResponse({
            "code": 1, 
            "msg": f"任务失败：{error}",
            "status": "failed"
        })
    else:
        return JsonResponse({
            "code": 0, 
            "msg": "任务处理中",
            "status": "processing"
        })
