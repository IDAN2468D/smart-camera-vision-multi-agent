@echo off
title Smart Camera Vision Multi-Agent System v2.0 Runner
echo ===============================================================
echo 🚀 SMART CAMERA VISION RECOGNITION MULTI-AGENT SYSTEM v2.0
echo 📦 Docker Ports: Frontend: 3002 ^| Backend: 5005
echo 📦 Local  Ports: Frontend: 3000 ^| Backend: 5000
echo ===============================================================
echo.
echo Choose execution mode:
echo [1] Run in Docker Containers (Recommended - Frontend: http://localhost:3002)
echo [2] Run Locally on Windows Host (Frontend: http://localhost:3000)
echo.
set /p mode="Enter choice [1 or 2] (Default 1): "

if "%mode%"=="2" (
    echo Starting Flask & Multi-Agent Backend locally on Port 5000...
    start "Vision Backend (Flask & OpenCV)" cmd /k "venv\Scripts\python main.py"
    echo Waiting 2 seconds for backend initialization...
    timeout /t 2 /nobreak >nul
    echo Starting Next.js Frontend locally on Port 3000...
    start "Vision Frontend (Next.js)" cmd /k "cd frontend && npm run dev"
    echo.
    echo 🌐 Open your browser at: http://localhost:3000
) else (
    echo Starting Docker Compose stack (Backend + Frontend)...
    docker compose up -d
    echo.
    echo 🌐 System is UP! Open your browser at: http://localhost:3002
    echo 📊 Backend Health: http://localhost:5005/api/health
)
