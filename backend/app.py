from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from models import (
    ResumeParsed,
    ResumeKeyInfo,
    ResumeFullInfo,
    JobRequest,
    MatchResponse,
)
from parser import parse_pdf_resume
from ai_utils import extract_key_info, compute_resume_id, compute_match_score
from cache import cache_resume, get_cached_resume, cache_match, get_cached_match

app = FastAPI(
    title="AI Resume Matcher",
    description="简历上传解析 + 关键信息提取 + JD 匹配评分",
    version="1.0.0",
)

# CORS：允许前端页面访问（GitHub Pages）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境可以改成你的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Resume matcher backend running"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)) -> Dict[str, Any]:
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    file_bytes = await file.read()
    raw_text, cleaned_text = parse_pdf_resume(file_bytes)

    if not cleaned_text.strip():
        raise HTTPException(status_code=400, detail="无法从简历中提取文本")

    resume_id = compute_resume_id(cleaned_text)

    # 缓存中是否已有
    cached = get_cached_resume(resume_id)
    if cached:
        return cached

    parsed = ResumeParsed(raw_text=raw_text, cleaned_text=cleaned_text)
    key_info: ResumeKeyInfo = extract_key_info(cleaned_text)

    full_info = ResumeFullInfo(
        resume_id=resume_id,
        parsed=parsed,
        key_info=key_info,
    )

    result = {"resume": full_info.dict()}
    cache_resume(resume_id, result)

    return result


@app.post("/match-job", response_model=MatchResponse)
async def match_job(req: JobRequest) -> MatchResponse:
    if not req.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description 不能为空")

    resume_data = get_cached_resume(req.resume_id)
    if not resume_data:
        raise HTTPException(status_code=404, detail="未找到对应简历，请先上传")

    resume = ResumeFullInfo(**resume_data["resume"])

    cache_key = f"{req.resume_id}:{hash(req.job_description)}"
    cached_match = get_cached_match(cache_key)
    if cached_match:
        return MatchResponse(**cached_match)

    match_score = compute_match_score(resume.parsed.cleaned_text, req.job_description)

    resp = MatchResponse(
        resume=resume,
        job_description=req.job_description,
        match_score=match_score,
    )

    cache_match(cache_key, resp.dict())
    return resp

