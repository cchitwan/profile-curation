#!/bin/bash

echo "🚀 Starting Resume Curation App..."

# 1. Kill existing processes on ports 8000 and 5173
echo "Stopping any existing services..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# 2. Start Backend
echo "Starting Backend on port 8000..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo "Backend started (logs in backend/backend.log)"
cd ..

# 3. Start Frontend
echo "Starting Frontend on port 5173..."
cd frontend
nohup npm run dev > frontend.log 2>&1 &
echo "Frontend started (logs in frontend/frontend.log)"
cd ..

echo "✅ All services are starting up!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
