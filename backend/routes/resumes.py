from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.db_models import User, Resume
from services.auth import get_current_user
from services.pdf_parser import extract_text_from_pdf

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported currently.")
    
    # Read file
    content = await file.read()
    
    # Extract Text
    try:
        raw_text = extract_text_from_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")
    
    # Save to DB
    new_resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        raw_text=raw_text,
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return {"message": "Resume uploaded successfully", "resume_id": new_resume.id}

@router.get("/all")
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()
    return [{
        "id": r.id,
        "filename": r.filename,
        "created_at": r.created_at
    } for r in resumes]

@router.get("/latest")
def get_latest_resume(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    return {
        "id": resume.id,
        "filename": resume.filename,
        "created_at": resume.created_at
    }
