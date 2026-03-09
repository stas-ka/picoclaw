@echo off
:: ============================================================
:: publish_release.bat — One-click publish a bot release
:: ============================================================
:: Double-click (or run) to package src/ and upload to
:: cloud.dev2null.de.  Requires Git Bash (git-scm.com).
:: ============================================================

:: Locate Git Bash
set GIT_BASH=C:\Program Files\Git\bin\bash.exe
if not exist "%GIT_BASH%" (
    set GIT_BASH=C:\Program Files (x86)\Git\bin\bash.exe
)
if not exist "%GIT_BASH%" (
    echo [ERROR] Git Bash not found at "%GIT_BASH%"
    echo         Install Git for Windows from https://git-scm.com/
    pause
    exit /b 1
)

:: Run the publish script (working dir = repo root)
set SCRIPT=%~dp0publish_release.sh
"%GIT_BASH%" --login -c "bash '%SCRIPT:\=/%'"
pause
