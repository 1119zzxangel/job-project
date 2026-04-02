#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    # 该脚本在项目根目录运行：python create_admin_user.py admin_user admin_pass
    if len(sys.argv) < 3:
        print('Usage: python create_admin_user.py <username> <password> [email]')
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else ''

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'JobRecommend.settings')
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import make_password
    from job.models import UserList

    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        print('Creating Django superuser', username)
        User.objects.create_superuser(username=username, email=email, password=password)
    else:
        print('Django user exists, skipping superuser creation')

    # 同步到 UserList 表，设置 role=admin
    if not UserList.objects.filter(user_id=username).exists():
        print('Creating UserList admin record')
        # store hashed password for UserList pass_word
        UserList.objects.create(user_id=username, user_name=username, pass_word=make_password(password), role='admin')
    else:
        ul = UserList.objects.get(user_id=username)
        if ul.role != 'admin':
            ul.role = 'admin'
            ul.save()
            print('Updated existing UserList to role=admin')
        else:
            print('UserList admin record already exists')

    print('Done.')
