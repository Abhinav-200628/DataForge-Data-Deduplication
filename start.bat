@echo off
title DATAFORGE Platform Launcher
echo ==========================================================
echo  Starting DATAFORGE Data Deduplication Platform
echo ==========================================================

echo [+] Launching FastAPI Backend (port 8000)...
start "DATAFORGE Backend (FastAPI)" cmd /k ".venv\Scripts\python.exe -m uvicorn deduplication.api.app:app --host 127.0.0.1 --port 8000 --reload"

echo [+] Launching React/Vite Frontend (port 5173)...
start "DATAFORGE Frontend (React/Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo [OK] Both services launched successfully!
echo      * Web Dashboard:  http://localhost:5173
echo      * API Swagger:    http://127.0.0.1:8000/docs
echo.

timeout /t 2 >nul
start http://localhost:5173

