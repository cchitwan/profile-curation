# AI-Powered Employee Profile Curation

A multi-agent AI web application built with FastAPI, LangGraph, Vite, and Vanilla JS. It curates a user's master resume against a specific job description to maximize ATS match scores.

## Project Structure
- `backend/`: FastAPI application containing the LangGraph multi-agent workflow.
- `frontend/`: Vite application with a modern Vanilla CSS design.

---

## 🚀 How to Start the Services

### 1. Configure Environment Variables
You need to provide your Gemini API key to run the AI agents.
1. Navigate to the `backend/` directory.
2. Open the `.env` file.
3. Replace the placeholder with your actual key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Start the Backend
Open a terminal and run the following commands:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```
*The backend API will be running at `http://localhost:8000`*

### 3. Start the Frontend
Open a **new** terminal and run the following commands:
```bash
cd frontend
npm install
npm run dev
```
*The frontend UI will be running at `http://localhost:5173`*

---

## 🧪 Testing the Application

1. Open your browser and go to `http://localhost:5173`.
2. Register a new user (e.g., `test@example.com` / `password123`).
3. Under the "Your Master Resume" section, upload a sample PDF resume.
4. Under the "Tailor for a New Job" section, paste a job URL or raw text description.
5. Click **Start AI Curation**. The background agents will iterate over your resume until it hits >95% match with the provided job description!
