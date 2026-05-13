#!/bin/bash
# Start PSX Portfolio Tracker (backend + frontend)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting PSX Portfolio Tracker..."

# Function to kill process on a port
kill_port() {
    local port=$1
    local pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        echo "Port $port is occupied by PID $pid. Killing it..."
        kill -9 $pid 2>/dev/null
    fi
}

# Backend
echo "[1/2] Starting FastAPI backend on http://localhost:8000"
kill_port 8000
cd "$SCRIPT_DIR/backend"
/opt/homebrew/bin/python3.12 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Frontend
echo "[2/2] Starting React frontend on http://localhost:5173"
kill_port 5173
cd "$SCRIPT_DIR/frontend"
/opt/homebrew/bin/npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "App running at: http://localhost:5173"
echo "API docs at:    http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
