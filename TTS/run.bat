@echo off
REM run.bat - Launcher for the TTS API server (OmniVoice backend)
REM Windows equivalent of run.sh

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VENV_DIR=venv
set REQ_FILE=Requirements.txt

echo ======================================================================
echo  TTS API Server (OmniVoice backend) - Launcher
echo ======================================================================

REM 1) Check python is available
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python not found. Please install Python 3.10+ and add it to PATH.
    exit /b 1
)

REM 2) Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creating virtual environment in .\%VENV_DIR% ...
    python -m venv "%VENV_DIR%"
)

REM 3) Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM 4) Upgrade pip and install requirements
if exist "%REQ_FILE%" (
    for %%A in ("%REQ_FILE%") do set REQ_SIZE=%%~zA
    if !REQ_SIZE! GTR 0 (
        echo Installing dependencies from %REQ_FILE% ...
        python -m pip install --upgrade pip >nul
        pip install -r "%REQ_FILE%"
    ) else (
        echo WARNING: %REQ_FILE% is empty.
        echo          Skipping dependency install - make sure fastapi, uvicorn,
        echo          soundfile, torch and the omnivoice package are installed manually.
    )
) else (
    echo WARNING: %REQ_FILE% not found.
    echo          Skipping dependency install - make sure fastapi, uvicorn,
    echo          soundfile, torch and the omnivoice package are installed manually.
)

REM 5) Optional environment variables (uncomment / edit as needed)
REM set TTS_PORT=8000
REM set TTS_API_KEY=your-secret-key
REM set OMNIVOICE_REF_AUDIO=C:\Users\lotus\Desktop\omnivoice2\ref.wav
REM set TTS_AUDIO_DIR=C:\temp\tts_audio

REM 6) Run the server
echo ----------------------------------------------------------------------
echo Starting server...
echo ----------------------------------------------------------------------
python main.py

REM Alternative (equivalent), if you prefer running uvicorn directly with reload:
REM uvicorn main:app --host 0.0.0.0 --port %TTS_PORT% --reload

endlocal
pause
