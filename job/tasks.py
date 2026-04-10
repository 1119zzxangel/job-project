"""
简历解析功能
"""

import time
import os
import requests
import json
from job.utils.resume_parser import parse_resume_structured
from job.models import ModelConfig

def process_resume(text):
    """处理简历解析任务"""
    start_time = time.time()
    print(f"开始处理简历解析任务...")
    
    # 从环境变量获取 API 密钥
    API_KEY = os.getenv("VOLCANO_API_KEY")
    
    # 从数据库获取当前启用的模型配置
    try:
        current_model = ModelConfig.objects.filter(is_active=True).first()
        if current_model:
            DEEPSEEK_ENDPOINT_ID = current_model.endpoint_id
            print(f"使用数据库配置的模型：{current_model.model_name} ({current_model.model_type})")
        else:
            # 如果没有数据库配置，尝试从环境变量读取
            DEEPSEEK_ENDPOINT_ID = os.getenv("DEEPSEEK_ENDPOINT_ID")
            if not DEEPSEEK_ENDPOINT_ID:
                print("未配置模型，使用关键字解析")
                result = parse_resume_structured(text)
                result['parse_method'] = 'keyword'
                result['parse_status'] = 'success'
                return result
            print(f"使用环境变量配置的模型：{DEEPSEEK_ENDPOINT_ID}")
    except Exception as e:
        print(f"读取模型配置失败：{e}")
        # 回退到环境变量
        DEEPSEEK_ENDPOINT_ID = os.getenv("DEEPSEEK_ENDPOINT_ID")
        if not DEEPSEEK_ENDPOINT_ID:
            result = parse_resume_structured(text)
            result['parse_method'] = 'keyword'
            result['parse_status'] = 'success'
            return result
    
    # 提示词
    prompt = """请严格按照以下JSON格式输出，不添加任何其他内容：
{"skills": ["技能1", "技能2"], "education": "最高学历", "experience_year": 工作年限数字, "job_target": "期望岗位"}

从简历中提取：
- skills: 只保留技术技能（编程语言、框架、工具等），去重
- education: 最高学历
- experience_year: 工作年限（数字）
- job_target: 期望岗位

简历：
"""
    
    # 替换简历文本
    full_prompt = prompt + text
    
    # 火山引擎 API 地址
    API_URL = "https://ark-cn-beijing.bytedance.net/api/v3/chat/completions"
    
    # 尝试调用 API
    try:
        print("尝试调用火山引擎 DeepSeek V3.2 API...")
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        # 构建请求体
        data = {
            "model": DEEPSEEK_ENDPOINT_ID,  # 使用接入点ID作为模型
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        # 发送请求
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"API调用成功，响应内容：{content[:200]}...")
            
            # 尝试解析JSON响应
            try:
                # 提取JSON（可能有markdown代码块）
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    parsed = json.loads(json_match.group())
                    print(f"解析结果：{parsed}")
                    result = {
                        "skills": parsed.get('skills', []),
                        "education": parsed.get('education', ''),
                        "total_experience_years": parsed.get('experience_year', 0),
                        "job_target": parsed.get('job_target', '')
                    }
                    result['parse_method'] = 'llm'
                    result['parse_status'] = 'success'
                    return result
                else:
                    parsed = json.loads(content)
                    print(f"解析结果：{parsed}")
                    result = {
                        "skills": parsed.get('skills', []),
                        "education": parsed.get('education', ''),
                        "total_experience_years": parsed.get('experience_year', 0),
                        "job_target": parsed.get('job_target', '')
                    }
                    result['parse_method'] = 'llm'
                    result['parse_status'] = 'success'
                    return result
            except json.JSONDecodeError as e:
                print(f"JSON解析失败：{content}, 错误：{e}")
                # 使用备用解析方法
                result = parse_resume_structured(text)
                result['parse_method'] = 'keyword'
                result['parse_status'] = 'success'
                return result
        else:
            print(f"API调用失败：{response.status_code} - {response.text}")
            # 使用备用解析方法
            result = parse_resume_structured(text)
            result['parse_method'] = 'keyword'
            result['parse_status'] = 'success'
            return result
            
    except requests.exceptions.Timeout:
        print("API调用超时")
        # 使用备用解析方法
        result = parse_resume_structured(text)
        result['parse_method'] = 'keyword'
        result['parse_status'] = 'success'
        return result
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误：{e}")
        # 使用备用解析方法
        result = parse_resume_structured(text)
        result['parse_method'] = 'keyword'
        result['parse_status'] = 'success'
        return result
    except Exception as e:
        print(f"API调用失败：{e}")
        # 使用备用解析方法
        result = parse_resume_structured(text)
        result['parse_method'] = 'keyword'
        result['parse_status'] = 'success'
        return result
