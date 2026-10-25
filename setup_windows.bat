@echo off
REM One-time setup for LegalCompass Assistant.
setlocal
set "APP=%~dp0"

echo ============================================================
echo   Setting up LegalCompass Assistant
echo ============================================================

REM Check for mapping API (prefer internal mapping_api, fallback to ..\sanhita-bridge)
if exist "%APP%mapping_api\src\sb_api\main.py" (
  set "MAPPING_DIR=%APP%mapping_api"
  echo [*] Found internal mapping API in "%APP%mapping_api"
) else if exist "%APP%..\sanhita-bridge\src\sb_api\main.py" (
  set "MAPPING_DIR=%APP%..\sanhita-bridge"
  echo [*] Found mapping API in "%APP%..\sanhita-bridge"
) else (
  echo [!] Could not find mapping API in "%APP%mapping_api" or "%APP%..\sanhita-bridge".
  pause & exit /b 1
)

REM Setup Python virtual environment
set "VENV=%APP%.venv"
if not exist "%VENV%\Scripts\activate.bat" (
  if exist "%APP%..\sanhita-bridge\.venv\Scripts\activate.bat" (
    set "VENV=%APP%..\sanhita-bridge\.venv"
    echo [*] Using existing virtual environment in "%VENV%"
  ) else (
    echo [*] Creating Python virtual environment in "%VENV%" ...
    python -m venv "%VENV%" || (echo [!] Python not found. Install Python 3.10+ & pause & exit /b 1)
  )
)

call "%VENV%\Scripts\activate.bat"
echo [*] Upgrading pip...
python -m pip install --upgrade pip

if exist "%MAPPING_DIR%\requirements-api.txt" (
  echo [*] Installing mapping API dependencies...
  pip install -r "%MAPPING_DIR%\requirements-api.txt" || (pause & exit /b 1)
)

echo [*] Installing assistant backend dependencies...
pip install -r "%APP%backend\requirements.txt" || (pause & exit /b 1)

echo [*] Installing frontend dependencies...
cd /d "%APP%web"
call npm install || (echo [!] npm failed. Install Node.js 20+ & pause & exit /b 1)

echo.
echo ============================================================
echo   Setup complete! Now double-click start_windows.bat to launch.
echo ============================================================
pause
