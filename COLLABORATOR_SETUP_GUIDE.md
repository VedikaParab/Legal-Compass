# 🧭 LegalCompass Assistant — Complete Collaborator & Setup Guide

Welcome! This guide is written so you can get **LegalCompass** running on your local machine in just a few minutes without friction.

---

## 📌 Table of Contents
1. [What is LegalCompass?](#what-is-legalcompass)
2. [Step 0: Getting Access & Cloning the Repo](#step-0-getting-access--cloning-the-repo)
3. [Step 1: Check Prerequisites](#step-1-check-prerequisites)
4. [Step 2: How to Run (Choose Your Method)](#step-2-how-to-run-choose-your-method)
   - [Method A: Windows 1-Click Launch (Easiest for Windows)](#method-a-windows-1-click-launch-easiest-for-windows)
   - [Method B: Terminal Commands (macOS / Linux / Windows)](#method-b-terminal-commands-macos--linux--windows)
   - [Method C: Docker Compose (All OS)](#method-c-docker-compose-all-os)
5. [Step 3: Verify Everything Works](#step-3-verify-everything-works)
6. [Interactive Features to Try Out](#interactive-features-to-try-out)
7. [How to Stop & Restart the Project](#how-to-stop--restart-the-project)
8. [Troubleshooting & Common Issues](#troubleshooting--common-issues)

---

## What is LegalCompass?

India recently replaced its colonial-era criminal laws on **1 July 2024**:
- **IPC** (Indian Penal Code) ➔ **BNS** (Bharatiya Nyaya Sanhita)
- **CrPC** (Code of Criminal Procedure) ➔ **BNSS** (Bharatiya Nagarik Suraksha Sanhita)
- **IEA** (Indian Evidence Act) ➔ **BSA** (Bharatiya Sakshya Adhiniyam)

**LegalCompass** is a citizen-facing AI legal assistant that helps users understand:
1. **Which law applies to their situation by date** (offences before 1 July 2024 remain under IPC; on or after apply BNS).
2. **Old ↔ New Section counterpart lookup** with detailed transition and split-provision notes.
3. **Actionable next steps** (FIR filing, police escalation, helplines, free legal aid).
4. **Automated complaint drafting** (.docx download for Police Station, SP, or Magistrate).
5. **Masked summary generation** for consulting a lawyer with personal details automatically redacted.
6. **Full multilingual support** in **English**, **हिन्दी (Hindi)**, and **मराठी (Marathi)**.

---

## Step 0: Getting Access & Cloning the Repo

Because the repository is **Private**, you must be added as a collaborator first:
1. Share your GitHub username with Vedika.
2. Check your email or go to [https://github.com/VedikaParab/Legal-Compass/invitations](https://github.com/VedikaParab/Legal-Compass/invitations) and click **Accept Invitation**.
3. Open your terminal (or PowerShell) and clone the repository:
   ```bash
   git clone https://github.com/VedikaParab/Legal-Compass.git
   cd Legal-Compass
   ```

---

## Step 1: Check Prerequisites

Make sure you have installed:

| Tool | Minimum Version | Download Link | Verification Command |
|---|---|---|---|
| **Python** | 3.10 or newer (3.11/3.12 recommended) | [python.org](https://www.python.org/downloads/) | `python --version` |
| **Node.js & npm** | Node 20+ (LTS) | [nodejs.org](https://nodejs.org/) | `node -v` and `npm -v` |
| **Git** | Any modern version | [git-scm.com](https://git-scm.com/) | `git --version` |

> ⚠️ **Crucial for Windows Python installation:** During Python installation, make sure to check the box **"Add Python to PATH"**!

---

## Step 2: How to Run (Choose Your Method)

LegalCompass consists of three services:
- **Service 1:** Transition Mapping API (Port `8000`)
- **Service 2:** Assistant Backend (Port `8100`)
- **Service 3:** Next.js Web Frontend (Port `3000`)

---

### Method A: Windows 1-Click Launch (Easiest for Windows)

If you are on Windows, two batch files handle everything automatically:

1. **First-time setup (run once):**
   - Double-click **`setup_windows.bat`**.
   - This automatically creates a Python virtual environment (`.venv`), installs all Python backend and mapping packages, and runs `npm install` for the frontend.
   - Wait until you see: `Setup complete! Now double-click start_windows.bat to launch.`

2. **Start the app:**
   - Double-click **`start_windows.bat`**.
   - Three command prompt windows will open (Mapping API on 8000, Backend on 8100, Frontend on 3000).
   - Your default browser will automatically open [http://localhost:3000](http://localhost:3000).

---

### Method B: Terminal Commands (macOS / Linux / Windows)

Open **three separate terminal tabs** in the root `Legal-Compass` directory:

#### 🔹 Terminal 1: Mapping API (Port 8000)
```bash
cd mapping_api

# Create & activate a virtual environment
python3 -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements-api.txt

# Run the Mapping API service
# macOS / Linux:
PYTHONPATH=src SB_API_KEYS=dev-local-key uvicorn sb_api.main:app --port 8000 --reload
# Windows PowerShell:
# $env:PYTHONPATH="src"; $env:SB_API_KEYS="dev-local-key"; uvicorn sb_api.main:app --port 8000 --reload
```
*Health check:* Visit `http://localhost:8000/v1/meta` (should show JSON with dataset DOI and code names).

---

#### 🔹 Terminal 2: Assistant Backend (Port 8100)
```bash
cd backend

# Use the virtual environment
# macOS / Linux:
source ../mapping_api/.venv/bin/activate
# Windows PowerShell:
# ..\mapping_api\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Run the backend service
# macOS / Linux:
LEGALCOMPASS_API_KEY=dev-local-key uvicorn app.main:app --port 8100 --reload
# Windows PowerShell:
# $env:LEGALCOMPASS_API_KEY="dev-local-key"; uvicorn app.main:app --port 8100 --reload
```
*Health check:* Visit `http://localhost:8100/api/status` (should show `"legalcompass_api": true`).

---

#### 🔹 Terminal 3: Web Frontend (Port 3000)
```bash
cd web

# Install packages
npm install

# Start development server
npm run dev
```
*Open application:* Visit [http://localhost:3000](http://localhost:3000) in your browser!

---

### Method C: Docker Compose (All OS)

If you have Docker and Docker Compose installed:

```bash
docker compose up --build
```

Wait for the build to complete, then navigate to [http://localhost:3000](http://localhost:3000).

---

## Step 3: Verify Everything Works

| Service | Address | What You Should See |
|---|---|---|
| **Mapping API** | [http://localhost:8000/v1/meta](http://localhost:8000/v1/meta) | JSON response containing `"doi": "10.21227/h4wg-7413"` |
| **Backend API** | [http://localhost:8100/api/status](http://localhost:8100/api/status) | JSON response with `"legalcompass_api": true` |
| **Web Frontend** | [http://localhost:3000](http://localhost:3000) | Full LegalCompass web application with top bar and intake form |

---

## Interactive Features to Try Out

Once the app is running on [http://localhost:3000](http://localhost:3000), here are some great flows to test:

1. **Describe an Incident:**
   - Type a narrative: *"On 12 August 2024 in Mumbai, someone called me claiming to be from my bank and cheated me of Rs 50,000 via UPI."*
   - Answer the follow-up questions (e.g. date, financial loss, police status).
   - Notice the result dashboard:
     - Applies **BNS** (because the incident happened after 1 July 2024).
     - Shows counterpart sections (e.g., Cheating: IPC 420 ➔ **BNS 318(4)**).
     - Generates actionable steps and an evidence checklist.
     - Provides a masked lawyer summary ready to copy or download.

2. **Test Temporal Law Logic (Pre vs Post July 2024):**
   - Change the incident date to **15 January 2024** (prior to 1 July 2024).
   - Observe how the engine automatically switches to **IPC as the governing substantive law**, showing BNS numbers for cross-reference only.

3. **Try Document Upload & In-Browser OCR:**
   - Go to the **Upload Document** tab.
   - Upload any sample FIR, complaint PDF, or picture of a complaint.
   - The browser parses the text in memory (Tesseract.js OCR) without sending private files to any server.

4. **Switch Languages (Hindi & Marathi):**
   - Click the language toggle at the top right: **English · हिन्दी · मराठी**.
   - Notice that the questions, options, date parser, and statutory guidance seamlessly translate into Devanagari.

5. **Standalone Quick Tools:**
   - Use the **Section Converter** in the top navigation: type `420`, `IPC 302`, or `BNS 103` to view direct translations and split warnings.
   - Use the **Which Law Applies?** date tool to inspect any calendar date on a visual timeline.

---

## How to Stop & Restart the Project

- **To Stop:**
  - If you used `start_windows.bat`, simply close the three opened command prompt windows.
  - If you used terminal commands, press `Ctrl + C` in each of the three terminal tabs.
  - If you used Docker, press `Ctrl + C` or run `docker compose down`.

- **To Restart Later:**
  - On Windows: Just double-click `start_windows.bat` (you do **not** need to run `setup_windows.bat` again).
  - In terminals: Run the start commands in the three tabs (no need to reinstall dependencies).

---

## Troubleshooting & Common Issues

### 1. `uvicorn: command not found` or `python: command not found`
- **Cause:** Virtual environment not activated, or Python was not added to your system PATH.
- **Fix:** Make sure you activated the `.venv` (`source .venv/bin/activate` or `.\.venv\Scripts\activate`). On Windows, reinstall Python ensuring *"Add Python to PATH"* is checked.

### 2. Port already in use (`Port 8000`, `8100`, or `3000`)
- **Cause:** Another process or previous run of the app is still occupying the port.
- **Fix:**
  - **On Windows (PowerShell):**
    ```powershell
    # Find process on port 8000/8100/3000 and kill it:
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8100).OwningProcess -Force
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force
    ```
  - **On macOS / Linux:**
    ```bash
    kill -9 $(lsof -t -i:8000 -i:8100 -i:3000)
    ```

### 3. Website says "Failed to fetch" or backend status shows `legalcompass_api: false`
- **Cause:** Service order. The assistant backend on port `8100` needs the mapping API on port `8000` to be running first.
- **Fix:** Ensure Terminal 1 (port 8000) shows `"Uvicorn running on http://127.0.0.1:8000"`, then restart Terminal 2 (backend).

### 4. Windows PowerShell Script Execution Policy Error (`Activate.ps1 cannot be loaded`)
- **Cause:** Windows restricts running unauthenticated PowerShell scripts by default.
- **Fix:** Open PowerShell as Administrator and run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
  Or simply use standard Command Prompt (`cmd.exe`) or the provided `.bat` scripts.

### 5. `npm install` fails or hangs
- **Cause:** Outdated Node version or network timeout.
- **Fix:** Ensure you have Node.js 20 or newer (`node -v`). Try cleaning cache and reinstalling:
  ```bash
  cd web
  npm cache clean --force
  npm install
  ```

---

## Need Help?
If you run into any questions or edge cases while running the project, reach out to Vedika or create an issue on GitHub!
