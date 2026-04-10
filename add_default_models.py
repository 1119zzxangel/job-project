#!/usr/bin/env python3
"""
添加默认模型到数据库
"""

import os
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'JobRecommend.settings')
django.setup()

from job.models import ModelConfig

# 从 .env 文件读取模型配置
from dotenv import load_dotenv
load_dotenv()

def add_default_models():
    """添加默认模型配置"""
    
    # 模型配置列表
    models = [
        {
            'model_name': 'DeepSeek V3',
            'endpoint_id': os.getenv('DEEPSEEK_ENDPOINT_ID', 'ep-20260409190312-8bldb'),
            'model_type': 'deepseek',
            'description': 'DeepSeek V3 大模型，用于简历解析',
            'is_active': True  # 默认启用
        },
        {
            'model_name': 'Doubao',
            'endpoint_id': os.getenv('DOUBAO_ENDPOINT_ID', 'ep-20260409191109-cdpcq'),
            'model_type': 'doubao',
            'description': '豆包大模型，用于简历解析',
            'is_active': False
        }
    ]
    
    for model_data in models:
        try:
            # 检查是否已存在
            existing = ModelConfig.objects.filter(
                endpoint_id=model_data['endpoint_id']
            ).first()
            
            if existing:
                print(f"模型 {model_data['model_name']} 已存在，跳过")
                continue
            
            # 创建模型配置
            model = ModelConfig.objects.create(**model_data)
            print(f"成功添加模型：{model.model_name}")
        except Exception as e:
            print(f"添加模型 {model_data['model_name']} 失败：{e}")

if __name__ == "__main__":
    print("开始添加默认模型...")
    add_default_models()
    print("添加完成！")
