@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  GenieForge local build script (Windows)
REM
REM  Usage:
REM    build.bat [version] [--skip-frontend]
REM
REM  Examples:
REM    build.bat                  use version from backend/app/__init__.py
REM    build.bat 0.4.0            override version
REM    build.bat 0.4.0 --skip-frontend   skip frontend build
REM
REM  Output:
REM    dist\GenieForge\GenieForge.exe
REM    release\<version>\GenieForge-<version>-windows.zip
REM ============================================================

set VERSION=%1
if "%VERSION%"=="" (
    for /f "delims=" %%v in ('python scripts\get_version.py') do set VERSION=%%v
)
set SKIP_FRONTEND=0
if /i "%~2"=="--skip-frontend" set SKIP_FRONTEND=1

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python not found in PATH. Install Python 3.11+ first.
    exit /b 1
)

echo ============================================
echo  GenieForge build  v%VERSION%
echo ============================================

REM ---- [1/3] frontend build ----
if "%SKIP_FRONTEND%"=="1" (
    echo [1/3] skip frontend build
) else (
    echo [1/3] frontend build ^(npm run build^) ...
    pushd frontend
    call npm run build
    if errorlevel 1 (
        echo [ERROR] frontend build failed
        popd
        exit /b 1
    )
    popd
)

REM ---- [2/3] clean old artifacts + PyInstaller ----
echo [2/3] PyInstaller packaging ...
if exist build\genieforge rd /s /q build\genieforge
if exist dist\GenieForge rd /s /q dist\GenieForge
python -m PyInstaller --noconfirm build\genieforge.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    exit /b 1
)

REM ---- [3/3] zip + checksums ----
echo [3/3] creating zip ...
python scripts\make_zip.py %VERSION%

echo.
echo ============================================
echo  Build done!  v%VERSION%
echo  exe : %CD%\dist\GenieForge\GenieForge.exe
echo  zip : %CD%\release\%VERSION%\GenieForge-%VERSION%-windows.zip
echo ============================================
echo  Opening release folder...
start "" explorer "%CD%\release\%VERSION%"
exit /b 0
