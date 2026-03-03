@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "TEMP_CLONE=%TEMP%\vd-update-%RANDOM%"

echo ==========================================
echo   VIDEO DOWNLOAD - Update Main Files
echo ==========================================
echo.

REM ==========================================
REM 1. Check and install Git
REM ==========================================
set "GIT_EXE="

REM Check local git first
if exist ".\git\cmd\git.exe" (
    set "GIT_EXE=.\git\cmd\git.exe"
    echo [Git] Using local Git
    goto :git_found
)

REM Check git in PATH
for /f "delims=" %%i in ('where git 2^>nul') do (
    if not defined GIT_EXE (
        set "GIT_EXE=%%i"
        echo [Git] Using system Git
        goto :git_found
    )
)

REM Download portable Git
echo [Git] Git not found. Downloading portable MinGit...

set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/MinGit-2.44.0-64-bit.zip"
set "GIT_ZIP=%ROOT%\git-temp.zip"

powershell -Command "Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_ZIP%' -UseBasicParsing"
if errorlevel 1 (
    echo ERROR: Failed to download Git
    del "%GIT_ZIP%" 2>nul
    pause
    exit /b 1
)

if not exist ".\git" mkdir ".\git"
powershell -Command "Expand-Archive -Path '%GIT_ZIP%' -DestinationPath '.\git' -Force"
del "%GIT_ZIP%"

set "GIT_EXE=.\git\cmd\git.exe"
echo [Git] Portable Git installed

:git_found
echo.

REM ==========================================
REM 2. Clone repository to temp folder
REM ==========================================
echo [Clone] Cloning repository to temp folder...
echo         URL: https://github.com/p-fpv/videodownload-ytdlp-gui.git

if exist "%TEMP_CLONE%" rmdir /s /q "%TEMP_CLONE%"

"!GIT_EXE!" clone --depth 1 https://github.com/p-fpv/videodownload-ytdlp-gui.git "%TEMP_CLONE%"
if errorlevel 1 (
    echo ERROR: Failed to clone repository
    rmdir /s /q "%TEMP_CLONE%" 2>nul
    pause
    exit /b 1
)

echo [Clone] Done.
echo.

REM ==========================================
REM 3. Copy all files from repository
REM ==========================================
echo [Update] Copying all files from repository...

if not exist "%TEMP_CLONE%" (
    echo ERROR: Temp clone folder not found!
    pause
    exit /b 1
)

xcopy /E /Y /I /H "%TEMP_CLONE%\*.*" "%ROOT%\" >nul
echo   + All files updated from repository

echo [Clean] Removing temp clone folder...
rmdir /s /q "%TEMP_CLONE%"
echo [Clean] Done.
echo.

echo ==========================================
echo   Running dependency update...
echo ==========================================
echo.

call "%ROOT%\other\install_or_update_requirements.bat"

echo.
echo ==========================================
echo   Update Complete!
echo ==========================================
echo.
echo Run START.bat to launch the application.
echo.
pause
