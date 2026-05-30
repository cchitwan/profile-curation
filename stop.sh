#!/bin/bash

echo "🛑 Stopping Resume Curation App..."

# Kill backend on 8000
BACKEND_PID=$(lsof -ti:8000)
if [ -n "$BACKEND_PID" ]; then
    echo "Killing backend (PID: $BACKEND_PID)"
    kill -9 $BACKEND_PID
else
    echo "Backend was not running."
fi

# Kill frontend on 5173
FRONTEND_PID=$(lsof -ti:5173)
if [ -n "$FRONTEND_PID" ]; then
    echo "Killing frontend (PID: $FRONTEND_PID)"
    kill -9 $FRONTEND_PID
else
    echo "Frontend was not running."
fi

echo "✅ All services stopped."
