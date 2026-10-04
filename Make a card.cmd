@echo off
rem Windows: double-click from the extracted ComputAI folder.
cd /d "%~dp0"
py -3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0computai" recap --lang zh
    if errorlevel 1 pause
    exit /b
)
python -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if not errorlevel 1 (
    python "%~dp0computai" recap --lang zh
    if errorlevel 1 pause
    exit /b
)
python3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if not errorlevel 1 (
    python3 "%~dp0computai" recap --lang zh
    if errorlevel 1 pause
    exit /b
)
echo Python 3.8 or newer is required: https://www.python.org/downloads/
pause
exit /b 1
