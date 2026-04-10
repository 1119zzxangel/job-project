from django.contrib import admin

from job.models import JobData, UserList, UserExpect, SendList, ModelConfig

# 后台里面的认证和授权 可以隐藏掉
from django.contrib import admin
from django.contrib.auth.models import User, Group

# 取消注册 User 和 Group 模型
admin.site.unregister(User)
admin.site.unregister(Group)

# 设置管理后台的头部标题
admin.site.site_header = '招聘后台管理'
# 设置管理后台在浏览器标签页中显示的标题
admin.site.site_title = '招聘后台管理'
# 设置管理后台主页的标题
admin.site.index_title = '招聘后台管理'

class UserListAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'user_name', 'email', 'phone', 'role')  # 列表中显示的字段
    search_fields = ('user_id', 'user_name', 'email', 'phone')  # 可搜索的字段
    list_filter = ('role',)  # 过滤字段
    # 设置默认的排序方式，这里按照 id 字段进行排序
    ordering = ['user_id']

admin.site.register(UserList, UserListAdmin)

# Register your models here.
class JobDataAdmin(admin.ModelAdmin):
    list_display = (
    'job_id', 'name', 'company', 'place', 'salary', 'education', 'experience', 'required_skills')
    search_fields = ('name', 'company', 'place', 'key_word', 'required_skills')
    list_filter = ('education', 'experience', 'scale')
    # 设置默认的排序方式，这里按照 id 字段进行排序
    ordering = ['job_id']

admin.site.register(JobData, JobDataAdmin)



class UserExpectAdmin(admin.ModelAdmin):
    list_display = ('expect_id', 'user', 'key_word', 'place', 'desired_salary', 'desired_experience', 'desired_education')
    search_fields = ('user__user_id', 'key_word', 'place')
    ordering = ['expect_id']
    actions = ['one_click_match']

    def one_click_match(self, request, queryset):
        # 为所选用户执行推荐（基于现有 recommend_by_item_id），并在 admin 显示消息
        from job import job_recommend
        total = 0
        for expect in queryset:
            user_obj = expect.user
            if not user_obj:
                continue
            recs = job_recommend.recommend_by_item_id(user_obj.user_id, k=10)
            total += 1
        self.message_user(request, f"已为 {total} 个用户触发推荐（后台仅执行，不展示）。")

admin.site.register(UserExpect, UserExpectAdmin)

class SendListAdmin(admin.ModelAdmin):
    list_display = ('send_id', 'user_display', 'job_display')
    search_fields = ('user__user_id', 'job__name')
    ordering = ['send_id']

    def user_display(self, obj):
        try:
            return obj.user.user_name or obj.user.user_id
        except Exception:
            return '-' 
    user_display.short_description = '用户'

    def job_display(self, obj):
        try:
            return obj.job.name
        except Exception:
            return '-'
    job_display.short_description = '岗位'

admin.site.register(SendList, SendListAdmin)

class ModelConfigAdmin(admin.ModelAdmin):
    list_display = ('model_id', 'model_name', 'model_type', 'endpoint_id', 'api_url', 'is_active', 'created_at')
    search_fields = ('model_name', 'endpoint_id', 'model_type', 'api_url')
    list_filter = ('model_type', 'is_active')
    ordering = ('-is_active', '-created_at')
    actions = ['activate_model', 'deactivate_model']

    def activate_model(self, request, queryset):
        # 先将所有模型设置为非激活状态
        ModelConfig.objects.update(is_active=False)
        # 然后激活选中的模型
        updated = queryset.update(is_active=True)
        self.message_user(request, f"已激活 {updated} 个模型，并将其他模型设置为非激活状态")
    activate_model.short_description = '激活选中模型'

    def deactivate_model(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"已将 {updated} 个模型设置为非激活状态")
    deactivate_model.short_description = '停用选中模型'

admin.site.register(ModelConfig, ModelConfigAdmin)


