# DATAFORGE Full-Stack Launcher (PowerShell)
# Launches both the FastAPI backend and React/Vite frontend in separate windows and opens the browser.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting DATAFORGE Data Deduplication Platform" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Launch FastAPI Backend
Write-Host "[+] Launching FastAPI Backend (port 8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectDir'; Write-Host '--- DATAFORGE Backend Server (FastAPI) ---' -ForegroundColor Cyan; .\.venv\Scripts\python -m uvicorn deduplication.api.app:app --host 127.0.0.1 --port 8000 --reload"

# 2. Launch Vite Frontend
Write-Host "[+] Launching React + Vite Frontend (port 5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectDir\frontend'; Write-Host '--- DATAFORGE Web Dashboard (React/Vite) ---' -ForegroundColor Cyan; npm run dev"

Write-Host ""
Write-Host "[OK] Both services launched successfully!" -ForegroundColor Green
Write-Host "     * Web Dashboard:  http://localhost:5173" -ForegroundColor Yellow
Write-Host "     * API Swagger:    http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

