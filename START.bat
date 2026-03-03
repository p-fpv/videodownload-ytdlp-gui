@echo off
cd /d "%~dp0"

set "PYTHON_EXE=.\App\python\python.exe"
set "FFMPEG_EXE=.\App\ffmpeg.exe"

echo ==========================================
echo   VIDEO DOWNLOAD - Launcher
echo ==========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found!
    echo Please run install_or_update_requirements.bat first.
    echo.
    pause
    exit /b 1
)

if not exist "%FFMPEG_EXE%" (
    echo WARNING: FFmpeg not found!
    echo Some features may not work.
    echo Run install_or_update_requirements.bat to download FFmpeg.
    echo.
)

echo Starting server...
echo.
"%PYTHON_EXE%" .\App\app.py
pause