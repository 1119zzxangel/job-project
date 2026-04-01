from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def _skills_to_text(skills):
    if isinstance(skills, (list, tuple)):
        return ' '.join([s.replace('-', ' ') for s in skills])
    return str(skills)


def match_resume_to_jobs(resume_text: str, jobs: list, top_n: int = 5) -> list:
    """计算简历文本与岗位列表的匹配度，返回排序后的匹配结果。

    jobs: list of dicts: each dict has at least 'id', 'title', 'skills' (list)
    返回每项包含: id, title, score (0-1), missing_skills (list)
    """
    corpus = []
    job_texts = []
    for job in jobs:
        jt = _skills_to_text(job.get('skills', [])) + ' ' + job.get('description', '')
        job_texts.append(jt)
        corpus.append(jt)

    # 把简历放在最后一个文档位置
    corpus.append(resume_text)

    vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=500)
    X = vectorizer.fit_transform(corpus)

    job_vectors = X[:-1]
    resume_vector = X[-1]

    sims = cosine_similarity(resume_vector, job_vectors)[0]

    results = []
    for idx, job in enumerate(jobs):
        score = float(sims[idx])
        required_skills = set([s.lower() for s in job.get('skills', [])])
        # 简单判断是否包含技能：匹配关键词存在于简历文本
        resume_lower = resume_text.lower()
        present = set([s for s in required_skills if s in resume_lower])
        missing = list(required_skills - present)
        results.append({
            'id': job.get('id'),
            'title': job.get('title'),
            'score': round(score, 4),
            'missing_skills': missing,
            'required_skills': list(required_skills)
        })

    results = sorted(results, key=lambda x: x['score'], reverse=True)
    return results[:top_n]