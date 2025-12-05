from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ResumeParsed(BaseModel):
    raw_text: str = Field(..., description="原始提取的文本")
    cleaned_text: str = Field(..., description="清洗后的文本")


class ResumeKeyInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    job_intention: Optional[str] = None
    years_of_experience: Optional[float] = None
    education_background: Optional[str] = None
    extra: Dict[str, Any] = {}


class ResumeFullInfo(BaseModel):
    resume_id: str
    parsed: ResumeParsed
    key_info: ResumeKeyInfo


class JobRequest(BaseModel):
    resume_id: str
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

