import hashlib
import json
import os
import re
from typing import Dict, List

from openai import OpenAI

from models import ResumeKeyInfo, MatchScore

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def compute_resume_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------- 关键信息提取 ----------

def _call_gpt_for_key_info(text: str) -> Dict:
    system_prompt = (
        "你是一个简历解析助手，请从中文或英文简历文本中抽取关键信息。"
        "只用 JSON 格式回答，不要有多余文字。"
        "字段包括：name, phone, email, address, job_intention, "
        "years_of_experience, education_background, extra。"
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

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0)) if m else {}
    return data


def extract_key_info(text: str) -> ResumeKeyInfo:
    data = _call_gpt_for_key_info(text)

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

    years_of_experience = None
    if isinstance(years, (int, float)):
        years_of_experience = float(years)
    elif isinstance(years, str):
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


# ---------- JD 关键词 & 匹配打分 ----------

def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9_]+", text)
    freq: Dict[str, int] = {}
    for t in tokens:
        t = t.lower()
        if len(t) <= 1:
            continue
        freq[t] = freq.get(t, 0) + 1
    sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_tokens[:top_k]]


def _call_gpt_for_match_score(resume_text: str, job_text: str) -> Dict:
    system_prompt = (
        "你是一个招聘匹配评估助手。现在有一份候选人简历和一个岗位描述，"
        "请给出技能匹配、工作经验匹配、学历匹配和综合评分（0-1）。"
        "只输出 JSON，不要多余文字。"
        "字段包括：overall_score, skill_match_score, "
        "experience_match_score, education_match_score, keywords（数组）。"
    )
    user_prompt = f"""
岗位描述：
{job_text}

候选人简历：
{resume_text}

请根据以上内容进行评分。
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
        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0)) if m else {}
    return data


def compute_match_score(resume_text: str, job_text: str) -> MatchScore:
    data = _call_gpt_for_match_score(resume_text, job_text)

    def _num(v, default=0.0):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r"\d+(\.\d+)?", v)
            if m:
                return float(m.group(0))
        return default

    def _clip01(x):
        return max(0.0, min(1.0, x))

    overall = _clip01(_num(data.get("overall_score"), 0.0))
    skill = _clip01(_num(data.get("skill_match_score"), 0.0))
    exp = _clip01(_num(data.get("experience_match_score"), 0.0))
    edu = _clip01(_num(data.get("education_match_score"), 0.0))
    keywords = data.get("keywords") or extract_keywords(job_text, top_k=10)

    return MatchScore(
        overall_score=round(overall, 4),
        skill_match_score=round(skill, 4),
        experience_match_score=round(exp, 4),
        education_match_score=round(edu, 4),
        keywords=keywords,
    )
