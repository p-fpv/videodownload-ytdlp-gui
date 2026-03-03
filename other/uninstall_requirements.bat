@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM Get parent directory (script is in 'other' folder)
set "ROOT=%~dp0.."

echo ==========================================
echo   VIDEO DOWNLOAD - Uninstall Requirements
echo ==========================================
echo.
echo This will remove:
echo   - Python installation (App\python\)
echo   - FFmpeg (App\ffmpeg.exe)
echo   - Downloaded files (App\downloads\)
echo   - Log files (App\server.log)
echo   - Temporary files
echo.
echo Removing...
echo.

if exist "%ROOT%\App\python\" (
    echo Removing Python...
    rmdir /s /q "%ROOT%\App\python"
)

if exist "%ROOT%\App\ffmpeg.exe" (
    echo Removing FFmpeg...
    del /f /q "%ROOT%\App\ffmpeg.exe"
)

if exist "%ROOT%\App\downloads\" (
    echo Removing downloads...
    rmdir /s /q "%ROOT%\App\downloads"
)

if exist "%ROOT%\App\server.log" (
    echo Removing server.log...
    del /f /q "%ROOT%\App\server.log"
)

if exist "%ROOT%\App\get-pip.py" (
    echo Removing get-pip.py...
    del /f /q "%ROOT%\App\get-pip.py"
)

for %%f in (python-temp.zip ffmpeg-temp.zip) do (
    if exist "%ROOT%\%%f" (
        echo Removing %%f...
        del /f /q "%ROOT%\%%f"
    )
)

for /d %%d in ("%ROOT%\ffmpeg-temp*") do (
    if exist "%ROOT%\%%d" (
        echo Removing %%d...
        rmdir /s /q "%ROOT%\%%d"
    )
)

echo.
echo ==========================================
echo   Uninstall Complete!
echo ==========================================
echo.
echo Run other\install_or_update_requirements.bat to reinstall.
echo.
pause
