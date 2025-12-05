from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ResumeParsed(BaseModel):
    raw_text: str = Field(..., description="简历原始文本")
    cleaned_text: str = Field(..., description="清洗后的简历文本")


class ResumeKeyInfo(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    job_intention: Optional[str] = None
    years_of_experience: Optional[float] = None
    education_background: Optional[str] = None
    extra: Dict[str, Any] = {}


class ResumeFullInfo(BaseModel):
    resume_id: str
    parsed: ResumeParsed
    key_info: ResumeKeyInfo


class JobRequest(BaseModel):
    resume_id: Optional[str] = None
    job_description: str


class MatchScore(BaseModel):
    overall_score: float
    skill_match_score: float
    experience_match_score: float
    education_match_score: float
    keywords: List[str]


class MatchResponse(BaseModel):
    resume: ResumeFullInfo
    job_description: str
    match_score: MatchScore
