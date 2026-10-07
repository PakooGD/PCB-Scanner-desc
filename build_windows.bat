@echo off
setlocal

echo === PCB Microscope Scanner (desktop) — Windows build ===

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ with "Add to PATH".
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

pyinstaller --clean --noconfirm pcb-scanner.spec

echo.
echo ====================================================
echo Done: dist\pcb-scanner.exe
echo ====================================================
pause
endlocal