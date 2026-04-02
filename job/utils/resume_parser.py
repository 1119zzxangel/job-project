import io
import os

def parse_txt_file(path_or_file) -> str:
    """支持传入文件路径或 file-like 对象，返回文本内容（仅文本文件）。"""
    if hasattr(path_or_file, 'read'):
        # file-like
        content = path_or_file.read()
        if isinstance(content, bytes):
            try:
                return content.decode('utf-8', errors='ignore')
            except Exception:
                return content.decode('gbk', errors='ignore')
        return content

    with open(path_or_file, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def parse_pdf_file(path) -> str:
    """从 PDF 文件提取文本。若未安装 `pdfminer.six`，会抛出 ImportError。"""
    try:
        from pdfminer.high_level import extract_text
    except Exception as e:
        raise ImportError('缺少 pdfminer.six：pip install pdfminer.six') from e

    return extract_text(path)


def parse_docx_file(path) -> str:
    """从 DOCX 文件提取文本。若未安装 `python-docx`，会抛出 ImportError。"""
    try:
        import docx
    except Exception as e:
        raise ImportError('缺少 python-docx：pip install python-docx') from e

    doc = docx.Document(path)
    parts = [p.text for p in doc.paragraphs]
    return '\n'.join(parts)


def parse_file(path_or_file) -> str:
    """自动根据文件后缀选择解析器，支持 txt/pdf/docx 或 file-like 对象。

    保留原 `parse_txt_file` 的行为以兼容现有调用。
    """
    # file-like with name attr
    if hasattr(path_or_file, 'read') and hasattr(path_or_file, 'name'):
        name = path_or_file.name
    elif isinstance(path_or_file, str):
        name = path_or_file
    else:
        # fallback to txt read
        return parse_txt_file(path_or_file)

    ext = os.path.splitext(name)[1].lower()
    if ext == '.pdf':
        return parse_pdf_file(path_or_file if isinstance(path_or_file, str) else name)
    if ext in ('.docx', '.doc'):
        return parse_docx_file(path_or_file if isinstance(path_or_file, str) else name)
    return parse_txt_file(path_or_file)


def parse_resume_structured(text: str) -> dict:
    """对简历文本做简单的结构化解析，返回字段：
    - raw_text: 原始文本
    - skills: 列表（从候选技能库中匹配）
    - education: 最高学历（博士/硕士/本科/大专/高中/不限）
    - total_experience_years: 经验年数估计（整数）
    - experiences: 简单的工作经历段落列表
    """
    if not isinstance(text, str):
        try:
            text = text.decode('utf-8', errors='ignore')
        except Exception:
            text = str(text)

    lower = text.lower()

    # 候选技能（可扩展） - 更全面的词库，保持小且可维护
    SKILLS = [
        'python', 'java', 'c++', 'c#', 'javascript', 'typescript', 'sql', 'django', 'flask', 'fastapi',
        'react', 'angular', 'vue', 'node', 'express', 'spring', 'springboot', 'tensorflow', 'pytorch',
        'keras', 'linux', 'git', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'spark', 'hadoop',
        'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'rabbitmq', 'kafka', 'excel',
        'html', 'css', 'sass', 'less', 'rest', 'graphql', 'opencv', 'nlp', 'pandas', 'numpy', 'scipy'
    ]

    # 基于词边界的简单提取，避免误匹配
    skills = []
    import re
    for s in SKILLS:
        pattern = r"\b" + re.escape(s.lower()) + r"\b"
        if re.search(pattern, lower):
            skills.append(s)

    # 进一步用分词候选（使用空白和符号分割）做模糊匹配
    tokens = set([t.strip('.,()[]:;+-/\\').lower() for t in re.split(r'\s|[,;:/\\()]+', lower) if t])
    for t in tokens:
        if len(t) > 2 and t in SKILLS and t not in skills:
            skills.append(t)

    # 教育程度识别
    edu = '不限'
    if '博士' in text or 'phd' in lower:
        edu = '博士'
    elif '硕士' in text or 'master' in lower:
        edu = '硕士'
    elif '本科' in text or 'bachelor' in lower or 'b.sc' in lower or 'ba ' in lower:
        edu = '本科'
    elif '大专' in text or '专科' in text or 'associate' in lower:
        edu = '大专'
    elif '高中' in text or '中专' in text:
        edu = '高中'

    # 经验年数估计：寻找类似 "3年" 或年份区间 2018-2020
    import re
    years = 0
    # 年数字模式，如 3年，5年以上
    m = re.findall(r"(\d+)\s*年", text)
    if m:
        nums = [int(x) for x in m if x.isdigit()]
        if nums:
            years = max(nums)
    # 年份区间
    ranges = re.findall(r"(20\d{2})\s*[-~至]\s*(20\d{2})", text)
    if ranges:
        for a, b in ranges:
            try:
                years = max(years, int(b) - int(a))
            except Exception:
                pass

    # 简单抽取经历段落（按换行分段，取含年份或公司关键词的段落）
    experiences = []
    for para in [p.strip() for p in text.split('\n') if p.strip()]:
        if re.search(r"(\d{4}|公司|公司名称|公司：)", para):
            experiences.append(para)

    return {
        'raw_text': text,
        'skills': list(set(skills)),
        'education': edu,
        'total_experience_years': int(years),
        'experiences': experiences,
    }