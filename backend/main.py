import os
from dotenv import load_dotenv
# Load environment variables from .env file before any other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from models import db_models

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Curation API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import users, resumes, curation

app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(curation.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Resume Curation App API"}
