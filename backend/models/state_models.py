from typing import TypedDict, List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- Pydantic Models for LLM Structured Outputs ---

class WorkExperience(BaseModel):
    company: str
    role: str
    duration: str
    description: str
    bullets: List[str]

class Education(BaseModel):
    institution: str
    degree: str
    duration: str

class StructuredResume(BaseModel):
    contact_info: str = Field(description="Name, email, phone, etc.")
    summary: str = Field(description="Professional summary")
    social_links: List[Dict[str, str]] = Field(default_factory=list, description="List of {label, url} pairs")
    skills: List[str] = Field(description="List of technical and soft skills")
    experience: List[WorkExperience]
    education: List[Education]

class JobRequirements(BaseModel):
    role_title: str
    required_skills: List[str]
    nice_to_have_skills: List[str]
    key_responsibilities: List[str]
    core_keywords: List[str] = Field(description="Most important keywords to pass ATS")

class GapReport(BaseModel):
    missing_skills: List[str]
    missing_keywords: List[str]
    improvement_areas: List[str] = Field(description="Specific feedback on resume sections to improve")
    is_aligned: bool = Field(description="True if the role matches the candidate's career path/level")
    alignment_feedback: str = Field(description="Explanation of why the role is or isn't a good match")

class ScoreReport(BaseModel):
    score: int = Field(description="ATS Match Score from 0 to 100")
    feedback: str = Field(description="Reasoning for the score")
    remaining_gaps: List[str]
    domain_mismatch: bool = Field(default=False)

# --- LangGraph State Schema ---

class GraphState(TypedDict):
    job_id: int
    raw_resume_text: str
    job_input: str # URL or raw text
    
    # Processed Data
    structured_resume: Optional[Dict[str, Any]] # Dict representation of StructuredResume
    job_requirements: Optional[Dict[str, Any]] # Dict representation of JobRequirements
    gap_report: Optional[Dict[str, Any]]
    curated_resume: Optional[Dict[str, Any]]
    score_report: Optional[Dict[str, Any]]
    initial_score: Optional[int]
    improvement_bullets: List[str]
    token_usage: Dict[str, int] # {"input": X, "output": Y}
    
    iteration_count: int
