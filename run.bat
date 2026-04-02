@echo off
echo ========================================
echo   LAZART Signing Engine v1.0
echo   Starting on port 5555...
echo ========================================
echo.

cd /d "%~dp0"

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check if frontend is built
if not exist "static\index.html" (
    echo [Setup] Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo   Open http://localhost:5555 in your browser
echo   Press Ctrl+C to stop
echo.
python main.py
