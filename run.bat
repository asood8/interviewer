@echo off
rem Double-click this to start Interviewer. It sets everything up the first time.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating the virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :nopython
    echo Installing dependencies, this takes a few minutes...
    .venv\Scripts\python -m pip install --quiet --upgrade pip
    .venv\Scripts\python -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto :failed
)

if not exist ".env" (
    echo.
    echo No .env file yet, so there's no API key to use.
    echo   1. copy .env.example .env
    echo   2. open .env and put your key after ANTHROPIC_API_KEY=
    echo      ^(get one at https://console.anthropic.com^)
    echo.
    pause
    exit /b 1
)

echo Starting Interviewer. Close this window or press Ctrl+C to stop it.
start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 5; Start-Process 'http://localhost:8501'"
.venv\Scripts\python -m streamlit run app.py
pause
exit /b 0

:nopython
echo.
echo Python isn't installed, or isn't on your PATH. Install it from https://python.org
echo and tick "Add python.exe to PATH" during setup.
echo.
pause
exit /b 1

:failed
echo.
echo Installing the dependencies failed. Scroll up to see why.
echo.
pause
exit /b 1
