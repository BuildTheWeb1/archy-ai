# ArchyAI

## Project Overview

ArchyAI is a web-based SaaS for Romanian structural engineers. It automates a repetitive, time-consuming task they perform on every project: calculating the rebar schedule ("Extras de armătură") from structural PDF drawings.

Engineers upload 1–4 PDF pages (planșe de armare) from a construction project. The system analyses the drawings using Claude Vision API and produces a rebar schedule table with: mark number, diameter, steel type, piece count (Buc.), bar length, total length per diameter, and total weight.

The detailed extraction pipeline design is documented in `docs/extraction-pipeline-plan.md`.

## Tech Stack

### Frontend

- **Framework**: React 19 + TypeScript + Vite
- **Routing**: TanStack Router (file-based, URL-driven state)
- **Server state**: TanStack Query (data fetching, polling)
- **UI components**: shadcn/ui
- **Styling**: TailwindCSS

### Backend

- **API framework**: Python 3.12 + FastAPI
- **Vision AI**: Claude Vision API (claude-sonnet-4-20250514) via `anthropic` SDK
- **PDF → image**: PyMuPDF (fitz) — converts PDF pages to 300 DPI PNGs
- **Task queue**: None — FastAPI BackgroundTasks for async processing
- **Database**: None — local JSON metadata files
- **Object storage**: Local filesystem (`backend/uploads/`)
- **Auth**: None — Phase 3
- **Payments**: None — Phase 3

### Hosting (current: local dev only)

- **Frontend**: Vite dev server on localhost:5173
- **Backend**: uvicorn on localhost:8000

## Project Structure

```
archyai/
├── backend/
│   ├── main.py                        # FastAPI app — routes only, thin handlers
│   ├── schemas.py                     # Pydantic request/response models
│   ├── storage.py                     # Local JSON metadata + file path helpers
│   │
│   ├── pipeline/
│   │   ├── orchestrator.py            # Runs vision extraction → schedule rows
│   │   ├── vision_extractor.py        # Claude Vision API: PDF images → structured JSON
│   │   ├── weights.py                 # Weight constants (kg/m by diameter) + row builder
│   │   ├── models.py                  # RebarMark and ScheduleRow dataclasses
│   │   └── excel_export.py            # Schedule → Excel export
│   │
│   ├── uploads/                       # Runtime storage — gitignored
│   │   └── {project_id}/
│   │       ├── metadata.json
│   │       └── pdfs/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx             # Nav shell
│   │   │   ├── index.tsx              # Home / project list
│   │   │   └── projects/$projectId.tsx # Project detail: upload, extract, review
│   │   ├── components/
│   │   │   ├── ScheduleTable.tsx      # Editable rebar schedule with inline recalc
│   │   │   └── ConfidenceBadge.tsx    # High/medium/low confidence indicator
│   │   ├── lib/
│   │   │   └── api.ts                 # Axios client — all API calls
│   │   └── types.ts                   # Shared TypeScript interfaces
│   ├── vite.config.ts
│   └── package.json
│
├── docs/
│   └── extraction-pipeline-plan.md    # Detailed pipeline design + example trace
├── example-docs/                      # Test PDFs (structural drawings)
├── .env                               # API keys (gitignored)
└── start-dev.sh                       # Starts backend + frontend
```

## Development Flow

```bash
# Start everything
./start-dev.sh

# Backend only
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Frontend only
cd frontend && pnpm dev
```

The `.env` file at the repo root must contain `ANTHROPIC_API_KEY`.

## API Endpoints

```
POST  /api/projects                       Create a new project
GET   /api/projects/{id}                  Get project (poll for status)
POST  /api/projects/{id}/pdfs             Upload 1–4 PDF planșe de armare
POST  /api/projects/{id}/extract          Trigger rebar extraction (background)
PUT   /api/projects/{id}/schedule         Save engineer's edits to schedule
GET   /api/projects/{id}/schedule.xlsx    Download schedule as Excel
GET   /health
```

## Processing Pipeline

```
User uploads 1–4 PDF planșe de armare
      ↓
POST /api/projects/{id}/pdfs → saves PDFs
POST /api/projects/{id}/extract → triggers background extraction
      ↓
Background task:
  1. Convert each PDF page to 300 DPI PNG images (PyMuPDF)
  2. Send all images to Claude Vision API (claude-sonnet-4-20250514)
     with specialised Romanian structural engineering prompt
  3. Claude returns structured JSON: marks, diameters, counts, lengths
  4. Build schedule rows with weight calculations (kg/m constants)
  5. Save schedule to metadata.json
      ↓
Frontend polls GET /api/projects/{id} every 2s
  → When status = "ready": shows editable schedule table
  → Engineer reviews, corrects if needed, then exports to Excel
```

See `docs/extraction-pipeline-plan.md` for the full multi-step pipeline design, difficulty tiers, and example trace of all 11 marks.

## Key Design Principle

**Separate AI reading from code calculation.** AI extracts raw data from images (mark numbers, annotations, occurrences, dimensions). Code does all arithmetic (counts, total lengths, weights). This separation is critical — asking AI to both read and calculate produces unreliable results.

## Development Guidelines

### Do

- **Keep route handlers thin** — delegate all logic to pipeline modules.
- **Use Pydantic schemas** for all FastAPI request/response bodies.
- **Use TypeScript strict mode** — no `any`.
- **AI reads, code calculates** — never ask the vision model to do arithmetic.

### Don't

- **Don't put business logic in route handlers** — keep them thin.
- **Don't use `any` in TypeScript.**
- **Don't leave `console.log` or `print()` in committed code** — use the logger.
- **Don't ask AI to calculate** — code handles all math (counts, lengths, weights).

## Advisor delegation policy

This project has an `advisor` subagent (Opus) configured at `.claude/agents/advisor.md`. It exists to give a second opinion on consequential decisions.

### When to consult the advisor

Before implementing, delegate to the `advisor` subagent when about to:

- Choose between architectural options that are hard to reverse.
- Design a parser or extractor for messy real-world input (e.g. Romanian rebar annotations) where the strategy is not obvious.
- Pick a dependency or external service for a load-bearing concern.
- Introduce a new abstraction or pattern that other code will depend on.
- Make a data modeling decision that will be annoying to migrate later.
- Handle a failure mode where the "right" behavior is a product/UX judgment call.

### When NOT to consult the advisor

Do not delegate for straightforward implementation, obvious bug fixes, formatting, renaming, or questions with a single clearly correct answer.

### How to consult it

1. Write a tight brief: goal, current state, 2–3 options, specific question, relevant constraints.
2. Invoke the advisor subagent with that brief. Do not dump the whole conversation.
3. Read the recommendation. If you disagree, say so to the user and explain why.
4. If the advisor says "stop and clarify X", stop and ask the user.
5. Report back: what you asked, what was recommended, whether you're following it.
