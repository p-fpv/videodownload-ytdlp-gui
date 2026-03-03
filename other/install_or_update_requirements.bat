@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM Get parent directory (script is in 'other' folder)
set "ROOT=%~dp0.."
set "APP_DIR=%ROOT%\App"
set "PYTHON_DIR=%APP_DIR%\python"

echo ==========================================
echo   VIDEO DOWNLOAD - Installer
echo ==========================================
echo.

REM Check if Python already exists
if exist "%PYTHON_DIR%\python.exe" (
    echo Python found. Running update mode...
    echo.
    goto :update_packages
)

REM Download Python embeddable
echo [1/5] Downloading Python 3.12...
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
set "PYTHON_ZIP=%ROOT%\python-temp.zip"
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing"
if errorlevel 1 (
    echo ERROR: Failed to download Python
    del "%PYTHON_ZIP%" 2>nul
    pause
    exit /b 1
)

REM Extract Python
echo [2/5] Extracting Python...
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"
del "%PYTHON_ZIP%"

REM Configure Python for portable use (enable site-packages)
echo Configuring Python...
(
    echo python312.zip
    echo .
    echo import site
) > "%PYTHON_DIR%\python312._pth"

REM Download get-pip.py
echo [3/5] Getting pip...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%APP_DIR%\get-pip.py' -UseBasicParsing"

REM Install pip (disable cache via environment variable and temp dir)
echo Installing pip...
set "PIP_NO_CACHE_DIR=1"
set "PIP_CACHE_DIR=%TEMP%\pip_cache_nocache"
"%PYTHON_DIR%\python.exe" "%APP_DIR%\get-pip.py" --no-cache-dir --no-warn-script-location
if errorlevel 1 (
    echo ERROR: Failed to install pip
    pause
    exit /b 1
)
if exist "%PIP_CACHE_DIR%" rmdir /s /q "%PIP_CACHE_DIR%" 2>nul

:update_packages
REM Update/install required packages (site-packages enabled via python312._pth)
echo [4/5] Updating packages...
"%PYTHON_DIR%\python.exe" -m pip install --upgrade --no-cache-dir pip --no-warn-script-location

"%PYTHON_DIR%\python.exe" -m pip show yt_dlp >nul 2>&1
if errorlevel 1 (
    echo Installing yt_dlp...
    "%PYTHON_DIR%\python.exe" -m pip install --no-cache-dir yt_dlp --no-warn-script-location
) else (
    echo Updating yt_dlp...
    "%PYTHON_DIR%\python.exe" -m pip install --upgrade --no-cache-dir yt_dlp --no-warn-script-location
)

"%PYTHON_DIR%\python.exe" -m pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing flask...
    "%PYTHON_DIR%\python.exe" -m pip install --no-cache-dir flask --no-warn-script-location
) else (
    echo Updating flask...
    "%PYTHON_DIR%\python.exe" -m pip install --upgrade --no-cache-dir flask --no-warn-script-location
)

:check_ffmpeg
REM Check if FFmpeg exists
echo [5/5] Checking FFmpeg...
if exist "%APP_DIR%\ffmpeg.exe" (
    echo FFmpeg found. Skipping download.
    goto :complete
)

echo FFmpeg not found. Downloading...
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "FFMPEG_ZIP=%ROOT%\ffmpeg-temp.zip"
set "FFMPEG_DIR=%ROOT%\ffmpeg-temp"

powershell -Command "Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%' -UseBasicParsing"
if errorlevel 1 (
    echo WARNING: Failed to download FFmpeg.
    del "%FFMPEG_ZIP%" 2>nul
    goto :complete
)

echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"

for /d %%i in ("%FFMPEG_DIR%\ffmpeg-*") do set "FFMPEG_BUILD=%%i"
set "FFMPEG_EXE=%FFMPEG_BUILD%\bin\ffmpeg.exe"

if exist "%FFMPEG_EXE%" (
    echo Copying ffmpeg.exe...
    copy "%FFMPEG_EXE%" "%APP_DIR%\ffmpeg.exe"
) else (
    echo WARNING: ffmpeg.exe not found in archive.
)

echo Cleaning up...
rmdir /s /q "%FFMPEG_DIR%" 2>nul
del "%FFMPEG_ZIP%" 2>nul

:complete
echo.
echo ==========================================
echo   Done!
echo ==========================================
echo.
echo Run START.bat to launch the application.
echo.
pause
