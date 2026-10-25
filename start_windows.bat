@echo off
REM Starts the mapping API (8000), the assistant backend (8100) and the website (3000) in three windows.
setlocal
set "APP=%~dp0"

REM Detect mapping API
if exist "%APP%mapping_api\src\sb_api\main.py" (
  set "MAPPING_DIR=%APP%mapping_api"
) else if exist "%APP%..\sanhita-bridge\src\sb_api\main.py" (
  set "MAPPING_DIR=%APP%..\sanhita-bridge"
) else (
  echo [!] Could not find mapping API in "%APP%mapping_api" or "%APP%..\sanhita-bridge".
  pause & exit /b 1
)

REM Detect virtual environment
if exist "%APP%.venv\Scripts\activate.bat" (
  set "VENV=%APP%.venv\Scripts\activate.bat"
) else if exist "%APP%..\sanhita-bridge\.venv\Scripts\activate.bat" (
  set "VENV=%APP%..\sanhita-bridge\.venv\Scripts\activate.bat"
) else (
  echo [!] Virtual environment not found. Run setup_windows.bat first.
  pause & exit /b 1
)

set "KEY=dev-local-key"
REM Make Python read and write text files as UTF-8 on Windows
set "PYTHONUTF8=1"

echo Starting LegalCompass services...
start "1 - LegalCompass mapping API (8000)" cmd /k "cd /d "%MAPPING_DIR%" && call "%VENV%" && set "SB_API_KEYS=%KEY%" && set "PYTHONPATH=src" && uvicorn sb_api.main:app --port 8000"
timeout /t 4 >nul
start "2 - Assistant backend (8100)" cmd /k "cd /d "%APP%backend" && call "%VENV%" && set "LEGALCOMPASS_API_KEY=%KEY%" && uvicorn app.main:app --port 8100 --reload"
timeout /t 3 >nul
start "3 - Website (3000)" cmd /k "cd /d "%APP%web" && npm run dev"
timeout /t 8 >nul
start "" http://localhost:3000

echo Three windows opened. Close them to stop the app.
