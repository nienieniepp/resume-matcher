import hashlib
import re
from typing import List, Dict
from models import ResumeKeyInfo, MatchScore


def compute_resume_id(text: str) -> str:
    """
    用内容生成一个简历 ID（可作为缓存 key 的一部分）
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ====== 关键信息提取（示例：正则 + 可插 AI） ======

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(1[3-9]\d{9})|(\+?\d[\d -]{8,}\d)")


def extract_key_info_with_rules(text: str) -> ResumeKeyInfo:
    """
    简单规则抽取示例，你可以改为调用 LLM。
    """
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)

    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0) if phone_match else None

    # 非常简单地猜姓名：取前几行中最像姓名的一行（中文或英文）
    lines = text.splitlines()
    name = None
    if lines:
        first_line = lines[0].strip()
        if 2 <= len(first_line) <= 15:
            name = first_line

    # 这些信息你可以改用 LLM 提示词分析：
    job_intention = None
    years_of_experience = None
    education_background = None

    return ResumeKeyInfo(
        name=name,
        phone=phone,
        email=email,
        address=None,
        job_intention=job_intention,
        years_of_experience=years_of_experience,
        education_background=education_background,
        extra={},
    )


def extract_key_info(text: str) -> ResumeKeyInfo:
    """
    封装函数：你可以在这里切换为 AI 模型抽取
    如：
    1. 先规则抽取
    2. 再调用 LLM 做补全和纠错
    """
    # TODO: 如果接 LLM, 在这里发 prompt 并解析结果
    return extract_key_info_with_rules(text)


# ====== JD 关键词提取 + 匹配评分（简化示例） ======

def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    非常简陋的关键词提取，用分词 + 词频 / 停用词过滤即可。
    这里先简单 split，真实环境推荐用 jieba / HanLP 等。
    """
    tokens = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9_]+", text)
    freq: Dict[str, int] = {}
    for t in tokens:
        t = t.lower()
        if len(t) <= 1:
            continue
        freq[t] = freq.get(t, 0) + 1
    sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_tokens[:top_k]]


def simple_text_overlap_score(resume_text: str, job_text: str) -> float:
    """
    使用关键词交集做一个 0~1 粗略相似度
    """
    resume_keywords = set(extract_keywords(resume_text, top_k=30))
    job_keywords = set(extract_keywords(job_text, top_k=30))
    if not job_keywords:
        return 0.0
    overlap = resume_keywords & job_keywords
    return len(overlap) / len(job_keywords)


def compute_match_score(resume_text: str, job_text: str) -> MatchScore:
    """
    封装匹配度：
    - skill_match_score: 使用简单关键词重合度
    - experience / education 这里简单给固定值，真实可以根据 AI 抽取的年限和学历打分
    """
    skill_score = simple_text_overlap_score(resume_text, job_text)
    # TODO: 替换为 AI 相似度模型，提升精度
    experience_score = 0.7
    education_score = 0.8

    overall = 0.5 * skill_score + 0.3 * experience_score + 0.2 * education_score

    keywords = extract_keywords(job_text, top_k=10)

    return MatchScore(
        overall_score=round(overall, 4),
        skill_match_score=round(skill_score, 4),
        experience_match_score=experience_score,
        education_match_score=education_score,
        keywords=keywords,
    )
