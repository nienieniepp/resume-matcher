from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

from models import ResumeParsed, ResumeFullInfo, JobRequest, MatchResponse
from parser import parse_pdf_resume
from ai_utils import extract_key_info, compute_resume_id, compute_match_score
from cache import CacheClient

app = FastAPI(
    title="Resume Matcher API",
    description="基于阿里云 Serverless + Python 的简历分析与职位匹配服务",
    version="1.0.0",
)

# CORS（方便前端 GitHub Pages 调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Redis（这里用环境变量会更好）
cache = CacheClient(host="your-redis-host", port=6379, password="yourpassword")


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    上传 PDF 简历 + 解析 + 关键信息提取
    返回：resume_id + 解析结果 + 关键信息
    """
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    file_bytes = await file.read()

    # 解析 PDF
    raw_text, cleaned_text = parse_pdf_resume(file_bytes)

    if not cleaned_text.strip():
        raise HTTPException(status_code=400, detail="无法从简历中提取文本，请检查文件内容")

    resume_id = compute_resume_id(cleaned_text)

    # 缓存中是否已有解析结果
    cache_key = f"resume:{resume_id}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    parsed = ResumeParsed(raw_text=raw_text, cleaned_text=cleaned_text)
    key_info = extract_key_info(cleaned_text)

    full_info = ResumeFullInfo(
        resume_id=resume_id,
        parsed=parsed,
        key_info=key_info,
    )

    result = {
        "resume": full_info.dict()
    }

    cache.set_json(cache_key, result, expire_seconds=3600 * 24)

    return result


@app.post("/match-job", response_model=MatchResponse)
async def match_job(req: JobRequest):
    """
    接收岗位描述 + 简历 ID，计算匹配度
    """
    if not req.job_description:
        raise HTTPException(status_code=400, detail="job_description 不能为空")

    # 先从缓存拿简历解析信息
    if not req.resume_id:
        raise HTTPException(status_code=400, detail="需要提供 resume_id")

    cache_key = f"resume:{req.resume_id}"
    resume_data = cache.get_json(cache_key)
    if not resume_data:
        raise HTTPException(status_code=404, detail="未找到对应 resume_id，请先上传简历")

    resume = ResumeFullInfo(**resume_data["resume"])

    # 再看看是否已有匹配结果缓存
    match_cache_key = f"match:{req.resume_id}:{hash(req.job_description)}"
    cached_match = cache.get_json(match_cache_key)
    if cached_match:
        return cached_match

    # 使用 AI / 简单逻辑计算匹配度
    match_score = compute_match_score(resume.parsed.cleaned_text, req.job_description)

    resp = MatchResponse(
        resume=resume,
        job_description=req.job_description,
        match_score=match_score,
    )

    cache.set_json(match_cache_key, resp.dict(), expire_seconds=3600)

    return resp
