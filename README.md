# LegalCompass Assistant

A citizen-facing legal assistant built on the **LegalCompass IPC↔BNS mapping** (IEEE DataPort, DOI [10.21227/h4wg-7413](https://doi.org/10.21227/h4wg-7413)).

A user describes an incident in plain words; the app asks follow-up questions, decides **which legal code applies by date** (pre-reform IPC/CrPC or post-reform BNS/BNSS), lists **applicable sections with their old↔new counterparts**, shows **similar past cases**, suggests actionable **next steps** (FIR, escalation, helplines, free legal aid), and produces a **masked summary for a lawyer** with personal details redacted.

> **Disclaimer:** General legal information, not legal advice. Displayed prominently across every screen.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Web Frontend (Next.js 15)                │
│                 http://localhost:3000                  │
│       • Full-width responsive UI                       │
│       • Client-side OCR (Tesseract.js)                 │
│       • English, Hindi, & Marathi support              │
└───────────────────────────┬────────────────────────────┘
                            │ /api requests
                            ▼
┌────────────────────────────────────────────────────────┐
│             Assistant Backend (FastAPI)                │
│                 http://localhost:8100                  │
│       • Intake & offence rule extraction               │
│       • Masking & document parsing (PDF, DOCX)         │
│       • Complaint drafting & lawyer summary            │
│       • Optional: IL-TUR classifier & LLM integration  │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP requests
                            ▼
┌────────────────────────────────────────────────────────┐
│           LegalCompass Mapping API (FastAPI)           │
│                 http://localhost:8000                  │
│       • Section transition lookup (IPC↔BNS, etc.)      │
│       • Temporal applicability engine                  │
│       • Canonical statute & citation comparison        │
└────────────────────────────────────────────────────────┘
```

The repository includes a self-contained copy of the transition API (`mapping_api/`) and published datasets, so the entire stack runs out of the box with zero external repository dependencies.

---

## Key Features

### Phase 1: Core Legal Guidance
- **Incident Understanding:** Rule-based extraction of key facts: incident dates, state/city, financial loss, weapons, cyber/online, physical injury, relationship, number of accused, and current police status.
- **Offence Identification:** 31 offence categories (supporting English + common Hinglish/vernacular terms) mapped to legal provisions and refined through dynamic follow-up questions.
- **Date-Governed Law Determination:** Automatic temporal rule application: IPC applies for incidents before 1 July 2024; BNS applies on or after 1 July 2024; continuing offences are flagged for review.
- **Live Section Conversion:** Every provision is mapped to its counterpart with split-provision warnings (e.g. IPC 498A → BNS 85/86) and change notes.
- **Privacy-Preserving Lawyer Summary:** Automatically masks phone numbers, emails, Aadhaar/PAN, bank accounts, UPI IDs, and personal names.

### Phase 2: Document Processing & Multilingual Support
- **Document Upload & OCR:** Upload FIRs, complaints, or charge sheets (PDF, Word `.docx`, images). Scanned documents are parsed directly in the browser via Tesseract.js (no local OCR binary required).
- **Trilingual Interface:** Complete interface support for **English**, **हिन्दी (Hindi)**, and **मराठी (Marathi)**, including Devanagari numerals, localized offence terms, and regional date formats.
- **Automated Complaint Drafts:** Pre-filled `.docx` drafts ready for submission: Police Station (FIR), Superintendent of Police (escalation u/s 175(3) BNSS / 154(3) CrPC), and Magistrate application.
- **Interactive Tools:** Standalone Section Converter (`420` ↔ `318(4)`), Date-to-Law timeline checker, and evidence checklists.

---

## Prerequisites

Before running the application, make sure you have installed:

- **Python 3.10+** (Python 3.11 or 3.12 recommended; ensure `python` and `pip` are added to your system PATH)
- **Node.js 20+** and **npm** (download from [nodejs.org](https://nodejs.org/))
- *(Optional)* **Docker & Docker Compose** (for containerized setup)
- *(Optional)* **Tesseract OCR UB Mannheim** (only required if server-side OCR is preferred over default browser-based OCR)

---

## How to Run the Project

### Option 1: One-Click Launch on Windows (Recommended for Windows)

1. **One-time Setup:**
   - Double-click **`setup_windows.bat`**.
   - This script will automatically create a virtual environment, install all Python dependencies (for both the Mapping API and Assistant Backend), and run `npm install` for the web frontend.

2. **Launch Application:**
   - Double-click **`start_windows.bat`**.
   - Three console windows will open to run the services:
     - **Mapping API** on port `8000`
     - **Assistant Backend** on port `8100`
     - **Web Frontend** on port `3000`
   - Your browser will automatically open to `http://localhost:3000`.

3. **Stop Application:**
   - Simply close the opened command prompt windows.

---

### Option 2: Running via Terminal (Cross-Platform: Windows / macOS / Linux)

Open three terminal windows (or tabs) in the `legalcompass-app` root directory:

#### Terminal 1: Mapping API (Port 8000)
```bash
# Navigate to mapping_api directory
cd mapping_api

# Create and activate virtual environment (if not already created)
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements-api.txt

# Start Mapping API service
export SB_API_KEYS=dev-local-key    # On Windows PowerShell: $env:SB_API_KEYS="dev-local-key"
export PYTHONPATH=src               # On Windows PowerShell: $env:PYTHONPATH="src"
uvicorn sb_api.main:app --port 8000 --reload
```
*Health check:* Verify by visiting `http://localhost:8000/v1/meta`.

#### Terminal 2: Assistant Backend (Port 8100)
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
# On Windows:
..\mapping_api\.venv\Scripts\activate
# On macOS/Linux:
source ../mapping_api/.venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start backend orchestrator
export LEGALCOMPASS_API_KEY=dev-local-key   # On Windows PowerShell: $env:LEGALCOMPASS_API_KEY="dev-local-key"
uvicorn app.main:app --port 8100 --reload
```
*Health check:* Verify by visiting `http://localhost:8100/api/status`.

#### Terminal 3: Web Frontend (Port 3000)
```bash
# Navigate to web directory
cd web

# Install npm packages
npm install

# Start Next.js development server
npm run dev
```
*Open application:* Visit [http://localhost:3000](http://localhost:3000) in your browser.

---

### Option 3: Running with Docker Compose

You can start the full stack with a single command:

```bash
# Copy example configuration if needed
cp .env.example .env

# Build and start all three services
docker compose up --build
```

Access the frontend at `http://localhost:3000`.

---

## Online Deployment (Vercel + Render)

The project is pre-configured for free cloud deployment:
- **Frontend:** Deploy `web/` to **Vercel** with Next.js detection. Set `NEXT_PUBLIC_API_BASE` to your Render backend URL.
- **Backend & Mapping API:** Deploy the root repository to **Render** using the included `Dockerfile` and `render.yaml`.

For complete step-by-step instructions, see **[DEPLOY.md](DEPLOY.md)**.

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` or set environment variables in your environment:

| Variable | Default | Purpose |
|---|---|---|
| `LEGALCOMPASS_API` | `http://127.0.0.1:8000` | URL of the LegalCompass transition API |
| `LEGALCOMPASS_API_KEY` | `dev-local-key` | Shared API key between backend and mapping API |
| `LLM_API_KEY` | *(optional)* | Key for xAI Grok (`xai-...`) or Groq (`gsk_...`) for plain-language summaries |
| `LLM_MODEL` | *(auto-detected)* | Override default chat model |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origins for cross-origin requests |
| `SERVER_OCR` | `0` | Set to `1` to enable backend Tesseract OCR alongside browser OCR |

---

## Optional: Training Local IL-TUR Models

If you have access to the gated IL-TUR benchmark dataset on Hugging Face ([Exploration-Lab/IL-TUR](https://huggingface.co/datasets/Exploration-Lab/IL-TUR)):

```bash
cd backend
pip install -r requirements-scripts.txt
huggingface-cli login                       # Authenticate with HuggingFace token
python scripts/train_classifier.py          # Generates data/ipc_classifier.joblib
python scripts/build_case_index.py          # Generates data/case_index.joblib
```

*Note:* Trained `.joblib` files are strictly git-ignored to comply with the IL-TUR dataset license.

---

## Running Automated Tests

To run the backend test suite:

```bash
cd backend
# Ensure Mapping API is running on port 8000
LEGALCOMPASS_API_KEY=dev-local-key python -m pytest -v
```

The test suite validates:
- Pre- and post-July 1, 2024 temporal rules
- Section conversion & split-provision logic (e.g. IPC 498A)
- Add-on sections (IPC 34 / BNS 3(5))
- Date extraction & PII masking rules
- Mapping integrity across all 31 supported offence definitions

---

## License & Dataset Attribution

- **Transition Mapping Dataset:** IEEE DataPort, DOI [10.21227/h4wg-7413](https://doi.org/10.21227/h4wg-7413), licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Statute Source:** Legislative Department, Ministry of Law and Justice, Government of India.
