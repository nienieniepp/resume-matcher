import hashlib
import json
import os
import re
from typing import List, Dict

from openai import OpenAI

from models import ResumeKeyInfo, MatchScore

# 通过环境变量读取 OpenAI Key
# 在本地调试时，你可以在系统里配置：
#   export OPENAI_API_KEY="sk-xxx"  (mac/linux)
#   set OPENAI_API_KEY=sk-xxx      (windows)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========== 工具函数 ==========

def compute_resume_id(text: str) -> str:
    """
    用内容生成一个简历 ID（可作为缓存 key 的一部分）
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ========== 关键信息提取 ==========

def _call_gpt_for_key_info(text: str) -> Dict:
    """
    调用 GPT，让它从简历文本中抽取关键信息，返回一个 dict
    """
    system_prompt = (
        "你是一个简历解析助手，请从中文或英文简历文本中抽取关键信息。"
        "只用 JSON 格式回答，不要有多余文字。"
        "字段包括：name, phone, email, address, job_intention, years_of_experience, "
        "education_background, extra（可放任何你认为有用的其他信息）。"
    )

    user_prompt = f"以下是简历全文，请解析：\n\n{text}\n\n请用 JSON 返回。"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = resp.choices[0].message.content.strip()

    # content 预期是一段 JSON 文本
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 万一模型前后加了废话，尝试从里面提取 JSON
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {}

    return data


def extract_key_info(text: str) -> ResumeKeyInfo:
    """
    对外暴露的关键信息提取函数：
    - 先调用 GPT 抽取
    - 如果某些字段缺失，再用简单规则兜底
    """
    data = _call_gpt_for_key_info(text)

    # 简单兜底：用正则再抓一次 email / phone
    EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    PHONE_RE = re.compile(r"(1[3-9]\d{9})|(\+?\d[\d -]{8,}\d)")

    email = data.get("email")
    if not email:
        m = EMAIL_RE.search(text)
        if m:
            email = m.group(0)

    phone = data.get("phone")
    if not phone:
        m = PHONE_RE.search(text)
        if m:
            phone = m.group(0)

    name = data.get("name")
    address = data.get("address")
    job_intention = data.get("job_intention")
    years = data.get("years_of_experience")
    edu = data.get("education_background")
    extra = data.get("extra") or {}

    # year 可能是字符串，尽量转成数字
    years_of_experience = None
    if isinstance(years, (int, float)):
        years_of_experience = float(years)
    elif isinstance(years, str):
        # 尝试从字符串中抓数字
        m = re.search(r"\d+(\.\d+)?", years)
        if m:
            years_of_experience = float(m.group(0))

    return ResumeKeyInfo(
        name=name,
        phone=phone,
        email=email,
        address=address,
        job_intention=job_intention,
        years_of_experience=years_of_experience,
        education_background=edu,
        extra=extra,
    )


# ========== JD 关键词提取（可选，用于展示） ==========

def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    简单关键词提取，用于展示给前端。
    不需要太复杂。
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


# ========== 匹配评分 ==========

def _call_gpt_for_match_score(resume_text: str, job_text: str) -> Dict:
    """
    调用 GPT 让它给出匹配评分。
    返回 JSON dict。
    """

    system_prompt = (
        "你是一个招聘匹配评估助手。"
        "现在有一份候选人简历和一个岗位描述，请你给出匹配评分。"
        "只输出 JSON，不要输出多余文字。"
        "字段包括："
        "overall_score（0~1小数），"
        "skill_match_score（0~1），"
        "experience_match_score（0~1），"
        "education_match_score（0~1），"
        "keywords（岗位关键能力列表）。"
    )

    user_prompt = f"""
岗位描述（JD）：
{job_text}

候选人简历：
{resume_text}

请评估该候选人与岗位的匹配度，并用 JSON 格式返回上述字段。
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {}

    return data


def compute_match_score(resume_text: str, job_text: str) -> MatchScore:
    """
    对外暴露的匹配评分函数：
    - 调用 GPT 得到各项评分
    - 如果某些字段缺失，做简单兜底
    """
    data = _call_gpt_for_match_score(resume_text, job_text)

    def _num(v, default=0.0):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r"\d+(\.\d+)?", v)
            if m:
                return float(m.group(0))
        return default

    overall = _num(data.get("overall_score"), 0.0)
    skill = _num(data.get("skill_match_score"), 0.0)
    exp = _num(data.get("experience_match_score"), 0.0)
    edu = _num(data.get("education_match_score"), 0.0)
    keywords = data.get("keywords") or extract_keywords(job_text, top_k=10)

    # 限制在 0~1 范围
    def _clip01(x):
        return max(0.0, min(1.0, x))

    return MatchScore(
        overall_score=round(_clip01(overall), 4),
        skill_match_score=round(_clip01(skill), 4),
        experience_match_score=round(_clip01(exp), 4),
        education_match_score=round(_clip01(edu), 4),
        keywords=keywords,
    )
