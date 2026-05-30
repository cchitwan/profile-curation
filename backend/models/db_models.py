from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    social_links = Column(Text, nullable=True) # Stores JSON list of {label, url}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    curation_jobs = relationship("CurationJob", back_populates="user", cascade="all, delete-orphan")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False) 
    social_links = Column(Text, nullable=True) # JSON list of {label, url}
    structured_data = Column(Text, nullable=True) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="resumes")

class CurationJob(Base):
    __tablename__ = "curation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    base_resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_url_or_description = Column(Text, nullable=False)
    status = Column(String, default="pending") 
    final_score = Column(Integer, nullable=True)
    curated_resume_json = Column(Text, nullable=True) 
    initial_score = Column(Integer)
    improvement_summary = Column(Text) 
    token_usage = Column(Text) 
    company_name = Column(String)
    target_role = Column(String)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="curation_jobs")
