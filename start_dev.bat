@echo off
set LSE_DEV=1
echo ========================================
echo   Starting Backend and Frontend (Dev Mode)
echo ========================================

:: Start Backend in a new terminal window
echo [Setup] Starting Backend (Python main.py)...
start "Backend" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate.bat && python main.py"

echo [Setup] Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak >nul

:: Start Frontend in a new terminal window
echo [Setup] Starting Frontend (Vite npm run dev)...
start "Frontend" cmd /k "cd /d "%~dp0\frontend" && npm run dev -- --open"

echo.
echo Both servers are starting in separate windows.
echo - Backend usually runs on port 5555
echo - Frontend (Vite) usually runs on port 5173
echo.
echo Press any key to close this launcher script.
pause >nul
