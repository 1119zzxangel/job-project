from django.shortcuts import render, redirect
from django.http import JsonResponse
# Create your views here.
from job import models
import re
import builtins
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

spider_code = 0  # 定义全局变量，用来识别爬虫的状态，0空闲，1繁忙


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
    spider_info = models.SpiderInfo.objects.filter(spider_id=1).first()  # 查询爬虫程序运行的数据记录
    # print(spider_info)
    return render(request, "welcome.html", locals())


def spiders(request):
    # 权限检查：只有管理员可以访问
    if request.session.get('user_role') != 'admin':
        return redirect('login')
    global spider_code
    # print(spider_code)
    spider_code_1 = spider_code
    return render(request, "spiders.html", locals())


def start_spider(request):
    # 权限检查：只有管理员可以访问
    # 支持两种登录方式：1. 项目自定义登录（session 中的 user_role）2. Django admin 登录（is_superuser）
    if request.session.get('user_role') != 'admin' and not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({"code": 1, "msg": "无权限操作"})

    if request.method == "POST":
        # 1. 获取参数 + 全部设置默认值，防止 None
        key_word = request.POST.get("key_word", "")
        city = request.POST.get("city", "")
        page = request.POST.get("page", "1")  # 默认第1页
        role = request.POST.get("role", "")

        # 2. 页面强转 int，防止报错
        try:
            page_int = int(page)
        except:
            page_int = 1

        # 3. 安全获取爬虫模型（判断非空）
        spider_model = models.SpiderInfo.objects.filter(spider_id=1).first()
        if spider_model:  # 必须判断！否则 None 会炸
            spider_model.count = (spider_model.count or 0) + 1
            spider_model.page = (spider_model.page or 0) + page_int
            spider_model.save()

        spider_code = 1

        # 4. 执行爬虫
        if role == '猎聘网':
            spider_code = tools.lieSpider(key_word=key_word, city=city, all_page=page)
        elif role == '智联招聘':
            spider_code = tools.zhilianSpider(key_word=key_word, city=city, all_page=page)
        else:
            return JsonResponse({"code": 1, "msg": "不支持的爬虫类型"})

        # 5. 返回结果
        if spider_code == 0:
            return JsonResponse({"code": 0, "msg": f"{role}爬取成功!"})
        else:
            return JsonResponse({"code": 1, "msg": f"{role}爬取失败!"})

    return JsonResponse({"code": 1, "msg": "请使用POST请求"})



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


def upload_resume(request):
    """处理简历上传和匹配"""
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
            except Exception as e:
                return JsonResponse({"code": 1, "msg": f"匹配失败：{e}"})
            # 结构化解析简历
            structured = parse_resume_structured(text)

            # 处理匹配结果并计算分项得分（技能/经验/学历）以及综合得分（0-100）
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
                req_skills = [s.lower() for s in (job_info.get('key_word') or '').split() if s.strip()]
                # 如果岗位没有明确关键词，尝试从jobs结构中使用 skills 字段
                if not req_skills:
                    # 尝试从职位标签或描述中拆分关键词作为技能
                    key_word_field = job_info.get('key_word') or job_info.get('label') or job_info.get('name') or ''
                    req_skills = [s.lower() for s in re.split(r'[,;\s/\\|]+', key_word_field) if s]

                resume_skills = [s.lower() for s in structured.get('skills', [])]
                present = [s for s in req_skills if s in ' '.join(resume_skills)]
                missing = [s for s in req_skills if s not in present]

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

                # ==================== 最终得分 ====================
                struct_score = W_SKILLS * skills_score + W_EXP * exp_score + W_EDU * edu_score

                # 文本相似度（来自算法结果）
                text_sim = float(result.get('score', 0.0))

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

            return render(request, "resume_result.html", {"results": enhanced, 'resume': structured})
        else:
            return JsonResponse({"code": 1, "msg": f"仅接受以下文件类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"})
    
    else:
        return redirect('resume_match')

def match_report(request, job_id=None):
    """展示指定岗位的匹配报告（从 session 中读取上次上传的匹配结果）。"""
    enhanced = request.session.get('last_match_enhanced') or []
    structured = request.session.get('last_resume_structured') or {}
    if not enhanced:
        return JsonResponse({"code": 1, "msg": "未找到最近的匹配结果，请先上传简历进行匹配。"})
    # 支持通过参数 job_id 指定要展示的岗位
    if job_id is None:
        job_id = request.GET.get('job_id')
    target = None
    for e in enhanced:
        if str(e.get('id')) == str(job_id):
            target = e
            break
    if not target:
        # 默认取第一条
        target = enhanced[0]

    return render(request, 'match_report.html', {'resume': structured, 'report': target})


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
