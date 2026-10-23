@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 localdrop.py
) else (
    python localdrop.py
)
echo.
echo WarpCoil s-a inchis. Apasa o tasta pentru a inchide fereastra.
pause >nul
