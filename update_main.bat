@echo off
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

if exist ".\git\cmd\git.exe" (
    set "GIT_EXE=.\git\cmd\git.exe"
    echo [Git] Using local Git
    goto :git_found
)

for /f "delims=" %%i in ('where git 2^>nul') do (
    if not defined GIT_EXE (
        set "GIT_EXE=%%i"
        echo [Git] Using system Git
        goto :git_found
    )
)

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
REM 2. Clone repository
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
REM 3. Copy files (excluding update_main.bat)
REM ==========================================
echo [Update] Copying all files from repository...

if not exist "%TEMP_CLONE%" (
    echo ERROR: Temp clone folder not found!
    pause
    exit /b 1
)

REM Copy all files except update_main.bat
for /f "delims=" %%f in ('dir /b "%TEMP_CLONE%"') do (
    if not "%%f"=="update_main.bat" (
        if exist "%TEMP_CLONE%\%%f\" (
            xcopy /E /Y /I "%TEMP_CLONE%\%%f\*.*" "%ROOT%\%%f\" >nul
        ) else (
            copy /Y "%TEMP_CLONE%\%%f" "%ROOT%\%%f" >nul
        )
    )
)

REM Copy update_main.bat last (may fail if running, but that's ok)
copy /Y "%TEMP_CLONE%\update_main.bat" "%ROOT%\update_main.bat" >nul 2>&1
echo   + All files updated from repository

REM ==========================================
REM 4. Cleanup temp files
REM ==========================================
echo [Clean] Removing temp clone folder...
rmdir /s /q "%TEMP_CLONE%" 2>nul
del "%ROOT%\git-temp.zip" 2>nul
del "%ROOT%\python-temp.zip" 2>nul
del "%ROOT%\ffmpeg-temp.zip" 2>nul
rmdir /s /q "%ROOT%\ffmpeg-temp" 2>nul
echo [Clean] Done.
echo.

REM ==========================================
REM 5. Run dependency update
REM ==========================================
echo ==========================================
echo   Running dependency update...
echo ==========================================
echo.

call "%ROOT%\other\install_or_update_requirements.bat"

echo.
pause
