from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from database import get_db, SessionLocal
from models.db_models import User, Resume, CurationJob
from models.state_models import GraphState
from services.auth import get_current_user
from services.jd_scraper import scrape_job_description
from agents.graph import curation_graph

from fastapi.responses import StreamingResponse
from services.resume_generator import generate_resume_pdf, generate_resume_docx

router = APIRouter(prefix="/api/curation", tags=["curation"])

class CurationRequest(BaseModel):
    job_input: str # Can be a URL or raw text
    is_url: bool
    company_name: str
    target_role: str
    resume_id: Optional[int] = None # User can select a specific resume
    social_links: List[Dict[str, str]] = Field(default_factory=list)
    submitted_at: Optional[str] = None # Capture time from client system

def run_curation_workflow(job_id: int, user_id: int, base_resume_text: str, job_input: str, is_url: bool, social_links: List[Dict[str, str]] = None):
    db = SessionLocal()
    try:
        job = db.query(CurationJob).filter(CurationJob.id == job_id).first()
        job.status = "processing"
        db.commit()

        # Handle URL vs raw text
        actual_job_text = job_input
        if is_url:
            try:
                actual_job_text = scrape_job_description(job_input)
            except Exception as e:
                job.status = "failed"
                job.curated_resume_json = json.dumps({"error": f"Failed to scrape URL: {str(e)}"})
                db.commit()
                return

        # Prepare initial state
        initial_state: GraphState = {
            "job_id": job_id,
            "raw_resume_text": base_resume_text,
            "job_input": actual_job_text,
            "structured_resume": None,
            "job_requirements": None,
            "gap_report": None,
            "curated_resume": None,
            "score_report": None,
            "initial_score": None,
            "improvement_bullets": [],
            "token_usage": {"input": 0, "output": 0},
            "iteration_count": 0
        }

        # Inject social links into the starting resume data if provided
        initial_state["social_links"] = social_links or []

        # Run Graph
        final_state = curation_graph.invoke(initial_state)

        # Save results
        job.status = "completed"
        job.curated_resume_json = json.dumps(final_state["curated_resume"])
        job.final_score = final_state["score_report"]["score"]
        job.initial_score = final_state["initial_score"]
        job.improvement_summary = json.dumps(final_state["improvement_bullets"])
        job.token_usage = json.dumps(final_state["token_usage"])
        db.commit()

    except Exception as e:
        job = db.query(CurationJob).filter(CurationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.curated_resume_json = json.dumps({"error": str(e)})
            db.commit()
    finally:
        db.close()


@router.post("/start")
def start_curation(
    request: CurationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's base resume
    if request.resume_id:
        resume = db.query(Resume).filter(Resume.id == request.resume_id, Resume.user_id == current_user.id).first()
    else:
        resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
        
    if not resume:
        raise HTTPException(status_code=400, detail="Please upload a base resume first.")

    # Auto-versioning logic
    latest_job = db.query(CurationJob).filter(
        CurationJob.user_id == current_user.id,
        CurationJob.company_name == request.company_name,
        CurationJob.target_role == request.target_role
    ).order_by(CurationJob.version.desc()).first()
    
    new_version = (latest_job.version + 1) if latest_job else 1

    # Create Job record
    job_created_at = datetime.now(timezone.utc)
    if request.submitted_at:
        try:
            # Parse ISO format from frontend (e.g. 2024-04-22T...)
            job_created_at = datetime.fromisoformat(request.submitted_at.replace("Z", "+00:00"))
            # Ensure it is treated as UTC if it was captured as UTC but from system time
            if job_created_at.tzinfo is None:
                job_created_at = job_created_at.replace(tzinfo=timezone.utc)
        except:
            pass

    new_job = CurationJob(
        user_id=current_user.id,
        base_resume_id=resume.id,
        job_url_or_description=request.job_input,
        company_name=request.company_name,
        target_role=request.target_role,
        version=new_version,
        status="pending",
        created_at=job_created_at
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Start background task
    background_tasks.add_task(
        run_curation_workflow,
        new_job.id,
        current_user.id,
        resume.raw_text,
        request.job_input,
        request.is_url,
        request.social_links
    )

    return {"message": "Curation started", "job_id": new_job.id}

@router.post("/analyze")
def analyze_curation(
    request: CurationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Get Resume
    if request.resume_id:
        resume = db.query(Resume).filter(Resume.id == request.resume_id, Resume.user_id == current_user.id).first()
    else:
        resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
        
    if not resume:
        raise HTTPException(status_code=400, detail="Please upload a base resume first.")

    # 2. Extract job text if URL
    actual_job_text = request.job_input
    if request.is_url:
        from services.jd_scraper import scrape_job_description
        try:
            actual_job_text = scrape_job_description(request.job_input)
        except Exception as e:
            print(f"Failed to scrape JD: {e}")

    # 3. Create Job in 'analyzing' state
    new_job = CurationJob(
        user_id=current_user.id,
        base_resume_id=resume.id,
        job_url_or_description=actual_job_text,
        company_name=request.company_name,
        target_role=request.target_role,
        status="analyzing",
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # 4. Run Analysis synchronously (it's fast enough)
    from agents.graph import run_analysis_workflow
    result = run_analysis_workflow(
        new_job.id, 
        current_user.id, 
        resume.raw_text, 
        actual_job_text, 
        request.is_url
    )
    
    return result

@router.post("/confirm/{job_id}")
def confirm_curation(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(CurationJob).filter(CurationJob.id == job_id, CurationJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "pending"
    db.commit()

    resume = db.query(Resume).filter(Resume.id == job.base_resume_id).first()
    
    # Run the rest of the workflow in background
    from agents.graph import run_curation_from_analysis
    background_tasks.add_task(
        run_curation_from_analysis,
        job.id,
        current_user.id,
        resume.raw_text,
        job.job_url_or_description,
        "http" in job.job_url_or_description
    )
    
    return {"status": "started"}

@router.get("/status/{job_id}")
def get_curation_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(CurationJob).filter(CurationJob.id == job_id, CurationJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    duration = 0
    if job.updated_at and job.created_at:
        duration = (job.updated_at - job.created_at).total_seconds()

    response = {
        "id": job.id,
        "status": job.status,
        "score": job.final_score or 0,
        "initial_score": job.initial_score or 0,
        "time_taken": round(duration, 1),
        "improvements": json.loads(job.improvement_summary) if job.improvement_summary else [],
        "token_usage": json.loads(job.token_usage) if job.token_usage else {"input":0, "output":0},
        "curated_resume": json.loads(job.curated_resume_json) if job.curated_resume_json else None,
        "created_at": job.created_at.isoformat() + "Z" if job.created_at else None,
        "job_description": job.job_url_or_description
    }

    return response

@router.get("/history")
def get_curation_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    jobs = db.query(CurationJob).filter(CurationJob.user_id == current_user.id).order_by(CurationJob.created_at.desc()).all()
    return [{
        "id": j.id, 
        "status": j.status, 
        "score": j.final_score, 
        "initial_score": j.initial_score,
        "time_taken": round((j.updated_at - j.created_at).total_seconds(), 1) if j.updated_at else 0,
        "company": j.company_name,
        "role": j.target_role,
        "version": j.version,
        "improvements": json.loads(j.improvement_summary) if j.improvement_summary else [],
        "token_usage": json.loads(j.token_usage) if j.token_usage else {"input":0, "output":0},
        "date": j.created_at.isoformat() + "Z" if j.created_at else None, 
        "job_info": j.job_url_or_description[:100]
    } for j in jobs]

class ExtractRequest(BaseModel):
    job_input: str
    is_url: bool = False

@router.post("/extract-info")
def extract_info(request: ExtractRequest, current_user: User = Depends(get_current_user)):
    job_input = request.job_input
    is_url = request.is_url
    
    actual_job_text = job_input
    if is_url:
        try:
            actual_job_text = scrape_job_description(job_input)
        except:
            pass # Fallback to using the URL string itself for extraction if scrape fails
            
    from agents.nodes import extract_job_info_direct
    info = extract_job_info_direct(actual_job_text)
    return info

@router.delete("/{job_id}")
def delete_curation_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(CurationJob).filter(CurationJob.id == job_id, CurationJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Curation job not found")
    
    db.delete(job)
    db.commit()
    return {"status": "success"}

@router.get("/download/{job_id}/{file_format}")
def download_curated_resume(
    job_id: int,
    file_format: str,
    disposition: str = "attachment", # "attachment" or "inline"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(CurationJob).filter(CurationJob.id == job_id, CurationJob.user_id == current_user.id).first()
    if not job or not job.curated_resume_json:
        raise HTTPException(status_code=404, detail="Curated resume not found")
    
    resume_data = json.loads(job.curated_resume_json)
    
    # Generate Smart Filename
    co_prefix = (job.company_name or "COMP")[:4].upper()
    role_prefix = (job.target_role or "ROLE")[:4].upper()
    base_name = f"{co_prefix}_{role_prefix}_v{job.version}"

    if file_format == "pdf":
        buffer = generate_resume_pdf(resume_data)
        filename = f"{base_name}.pdf"
        media_type = "application/pdf"
    elif file_format == "docx":
        buffer = generate_resume_docx(resume_data)
        filename = f"{base_name}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'pdf' or 'docx'.")
        
    content_disposition = f"{disposition}; filename={filename}"
    
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition}
    )
