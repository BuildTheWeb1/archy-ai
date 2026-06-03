# ArchyAI

Automated rebar schedule extraction for Romanian structural engineers. Upload PDF structural drawings (planșe de armare), get back an editable "Extras de armătură" table with mark numbers, diameters, counts, lengths, and weights — ready to export as Excel.

## How it works

1. Create a project and upload 1–4 PDF pages (structural reinforcement drawings).
2. The backend converts each page to a 300 DPI image, sends them to Claude Vision API with a specialised Romanian structural engineering prompt.
3. Claude extracts raw data (mark numbers, diameters, piece counts, bar lengths). All arithmetic — total lengths, weights — is done in code, not by the AI.
4. The frontend displays an editable schedule table grouped by diameter, matching the standard Romanian format. Engineers review, correct if needed, then export to `.xlsx`.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, TanStack Router + Query, Tailwind CSS |
| Backend | Python 3.12, FastAPI |
| Vision AI | Claude Vision API (claude-sonnet-4-20250514) via `anthropic` SDK |
| PDF → image | PyMuPDF (fitz) — 300 DPI PNG conversion |
| Excel export | openpyxl |

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 20+ and pnpm
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
pnpm install
```

### Run

```bash
./start-dev.sh
```

| Service | URL |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/projects` | Create a new project |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/{id}` | Get project details (poll for status) |
| `DELETE` | `/api/projects/{id}` | Delete a project |
| `POST` | `/api/projects/{id}/pdfs` | Upload 1–4 PDF pages |
| `GET` | `/api/projects/{id}/pdfs` | List uploaded PDFs |
| `POST` | `/api/projects/{id}/extract` | Trigger rebar extraction (async) |
| `GET` | `/api/projects/{id}/schedule` | Get extracted schedule |
| `PUT` | `/api/projects/{id}/schedule` | Save engineer's edits |
| `GET` | `/api/projects/{id}/schedule/xlsx` | Download schedule as Excel |
| `GET` | `/health` | Health check |

## Project structure

```
archy-ai/
├── backend/
│   ├── main.py                     # FastAPI routes
│   ├── schemas.py                  # Pydantic models
│   ├── storage.py                  # Local JSON metadata + file helpers
│   ├── pipeline/
│   │   ├── orchestrator.py         # PDF → vision extraction → schedule
│   │   ├── vision_extractor.py     # Claude Vision API calls
│   │   ├── weights.py              # kg/m constants per diameter
│   │   ├── models.py               # RebarMark, ScheduleRow dataclasses
│   │   └── excel_export.py         # Schedule → .xlsx export
│   └── uploads/                    # Runtime file storage (gitignored)
├── frontend/
│   ├── src/
│   │   ├── routes/                 # TanStack Router file-based routes
│   │   ├── components/             # ScheduleTable, ConfidenceBadge
│   │   ├── lib/api.ts              # Axios API client
│   │   └── types.ts                # Shared TypeScript interfaces
│   └── package.json
├── example-docs/                   # Test PDFs (structural drawings)
├── start-dev.sh                    # Starts backend + frontend
└── .env.example
```

## Current status

MVP — fully functional locally. No auth, no cloud storage, no database (uses local JSON files). Extraction accuracy is validated against real structural drawings.
