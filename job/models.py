# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models





from django.db import models

class JobData(models.Model):
    job_id = models.AutoField('职位ID', primary_key=True)  # 职位ID，自动增长主键
    name = models.CharField('职位名称', max_length=255, blank=True, null=True)  # 职位名称
    salary = models.CharField('薪资', max_length=255, blank=True, null=True)  # 薪资
    place = models.CharField('工作地点', max_length=255, blank=True, null=True)  # 工作地点
    education = models.CharField('学历要求', max_length=255, blank=True, null=True)  # 学历要求
    experience = models.CharField('工作经验', max_length=255, blank=True, null=True)  # 工作经验
    company = models.CharField('公司名称', max_length=255, blank=True, null=True)  # 公司名称
    label = models.CharField('职位标签', max_length=255, blank=True, null=True)  # 职位标签
    scale = models.CharField('公司规模', max_length=255, blank=True, null=True)  # 公司规模
    href = models.CharField('职位链接', max_length=255, blank=True, null=True)  # 职位链接
    key_word = models.CharField('关键词', max_length=255, blank=True, null=True)  # 关键词
    required_skills = models.CharField('必需技能(逗号分隔)', max_length=1024, blank=True, null=True)
    required_skills = models.CharField('必需技能(逗号分隔)', max_length=1024, blank=True, null=True)

    class Meta:
        managed = True  # 是否由Django管理
        db_table = 'job_data'  # 数据库表名
        verbose_name = "招聘信息"
        verbose_name_plural = "招聘信息"

    def __str__(self):
        return self.name or str(self.job_id)


class SendList(models.Model):
    send_id = models.AutoField('投递ID', primary_key=True)
    job = models.ForeignKey(JobData, models.DO_NOTHING, blank=True, null=True, verbose_name='岗位')
    user = models.ForeignKey('UserList', models.DO_NOTHING, blank=True, null=True, verbose_name='用户')

    class Meta:
        managed = True
        db_table = 'send_list'
        verbose_name = '投递记录'
        verbose_name_plural = '投递记录'

    def __str__(self):
        try:
            return f"{self.user} - {self.job}"
        except Exception:
            return str(self.send_id)


class SpiderInfo(models.Model):
    spider_id = models.AutoField('爬虫ID', primary_key=True)
    spider_name = models.CharField('爬虫名称', max_length=255, blank=True, null=True)
    count = models.IntegerField('抓取数量', blank=True, null=True)
    page = models.IntegerField('爬取页数', blank=True, null=True)
    last_run = models.DateTimeField('最后爬取时间', blank=True, null=True)
    STATUS_CHOICES = (
        ('idle', '空闲'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
    )
    status = models.CharField('爬取状态', max_length=16, choices=STATUS_CHOICES, default='idle')

    class Meta:
        managed = True
        db_table = 'spider_info'
        verbose_name = '爬虫信息'
        verbose_name_plural = '爬虫信息'

    def __str__(self):
        return self.spider_name or f"Spider {self.spider_id}"


class UserExpect(models.Model):
    expect_id = models.AutoField('期望ID', primary_key=True)
    key_word = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey('UserList', models.DO_NOTHING, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    desired_salary = models.CharField('期望薪资', max_length=64, blank=True, null=True)
    desired_experience = models.CharField('期望经验', max_length=64, blank=True, null=True)
    desired_education = models.CharField('期望学历', max_length=64, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'user_expect'
        verbose_name = '求职期望'
        verbose_name_plural = '求职期望'

    def __str__(self):
        try:
            return f"{self.user} -> {self.key_word} @ {self.place}"
        except Exception:
            return str(self.expect_id)



class UserList(models.Model):
    ROLE_CHOICES = (
        ('user', '普通用户'),
        ('admin', '管理员'),
    )
    user_id = models.CharField('用户ID', primary_key=True, max_length=11)  # 用户ID，主键
    user_name = models.CharField('用户名', max_length=255, blank=True, null=True)  # 用户名
    pass_word = models.CharField('密码', max_length=255, blank=True, null=True)  # 密码（已哈希）
    email = models.CharField('邮箱', max_length=255, blank=True, null=True)
    phone = models.CharField('联系电话', max_length=32, blank=True, null=True)
    avatar = models.CharField('头像路径', max_length=512, blank=True, null=True)
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='user')  # 角色字段
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    reset_token = models.CharField('重置Token', max_length=128, blank=True, null=True)
    reset_token_expiry = models.DateTimeField('重置Token过期时间', blank=True, null=True)

    class Meta:
        managed = True  # 是否由Django管理
        db_table = 'user_list'  # 数据库表名
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.user_name or self.user_id