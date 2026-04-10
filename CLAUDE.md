# ArchyAI

## Project Overview

ArchyAI is a web-based SaaS for Romanian structural engineers and architects. It automates two things they currently do manually:
1. Takes an uploaded `.dwg` file and converts it to a high resolution pdf, ready to print or send to clients.
2. will be refined soon enough

## Tech Stack

### Frontend

- **Framework**: React 19 + TypeScript + Vite
- **Routing**: TanStack Router (file-based, URL-driven state)
- **Server state**: TanStack Query (data fetching, polling)
- **UI components**: [shadcn/ui]
- **Styling**: TailwindCSS
- **Linting**: Biome

### Backend

- **API framework**: Python 3.12 + FastAPI
- **DWG/DXF → PDF**: Autodesk Platform Services (APS) Model Derivative API — cloud conversion with full AutoCAD fidelity
- **PDF splitting**: PyMuPDF — splits combined PDF into per-layout pages
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
│   ├── main.py              # FastAPI app — routes only, thin handlers
│   ├── converter.py         # APS API: DWG/DXF → PDF → split per layout
│   ├── splitter.py          # Bundle layout PDFs into ZIP
│   ├── storage.py           # Local JSON metadata + file path helpers
│   ├── schemas.py           # Pydantic request/response models
│   │
│   ├── weights.py           # Material weight constants (kg/m by diameter)
│   │
│   ├── uploads/             # Runtime storage — gitignored
│   │   └── {drawing_id}/
│   │       ├── metadata.json
│   │       ├── original.dwg/.dxf
│   │       └── layouts/0.pdf, 1.pdf, …
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx              # Nav shell
│   │   │   ├── index.tsx               # Upload page
│   │   │   └── drawings/$drawingId.tsx # Drawing detail (layouts list)
│   │   ├── components/
│   │   │   ├── FileUpload.tsx          # Drag-and-drop DWG upload
│   │   │   ├── DrawingDetail.tsx       # Polling + status + layout list
│   │   │   └── LayoutList.tsx          # Grid of layout cards with downloads
│   │   ├── lib/
│   │   │   └── api.ts                  # Axios client — all API calls
│   │   ├── routeTree.gen.ts            # Auto-generated — do not edit
│   │   └── types.ts                    # Shared TypeScript interfaces
│   ├── vite.config.ts
│   └── package.json
│
├── example-docs/                       # Expected output PDFs (1.pdf–17.pdf)
├── .env                                # APS credentials (gitignored)
└── start-dev.sh                        # Starts backend + frontend
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

The `.env` file at the repo root is loaded by `start-dev.sh`. Set `APS_CLIENT_ID` and `APS_CLIENT_SECRET` with your Autodesk Platform Services credentials (create an app at https://aps.autodesk.com/myapps).

## API Endpoints

```
POST  /api/drawings/upload              Upload DWG/DXF → triggers background rendering
GET   /api/drawings/{id}                Poll status: processing | ready | error
GET   /api/drawings/{id}/layouts/{n}/pdf  Download single layout PDF
GET   /api/drawings/{id}/download       Download ZIP of all layouts
GET   /health
```

## Processing Pipeline

```
User uploads .dwg or .dxf
      ↓
POST /api/drawings/upload
  → saves file to uploads/{id}/original.dwg (or .dxf)
  → sets status = "processing"
  → returns {id, status: "processing"} immediately
      ↓
Background task (_process_drawing):
  1. Authenticate with Autodesk Platform Services (APS)
  2. Upload DWG/DXF to APS Object Storage
  3. Submit Model Derivative translation job (PDF output)
  4. Poll until translation completes
  5. Download combined PDF, split into per-page PDFs (PyMuPDF)
  6. Update metadata.json: status = "ready", layouts = [{index, name}]
      ↓
Frontend polls GET /api/drawings/{id} every 2s
  → When status = "ready": shows layout list with download buttons
```

## Development Guidelines

### Do

- **Keep route handlers thin** — delegate all logic to `converter.py`, `splitter.py`, etc.
- **Use Pydantic schemas** for all FastAPI request/response bodies.
- **Use TypeScript strict mode** — no `any`.
- **Fail loudly on missing APS credentials** — raise a clear error if `APS_CLIENT_ID` / `APS_CLIENT_SECRET` are not set.

### Don't

- **Don't put business logic in route handlers** — keep them thin.
- **Don't use `any` in TypeScript.**
- **Don't leave `console.log` or `print()` in committed code** — use the logger.

## Advisor delegation policy

This project has an `advisor` subagent (Opus) configured at `.claude/agents/advisor.md`. It exists to give you a second opinion from a stronger model on consequential decisions, while you (Sonnet) stay the executor and drive the actual work.

### When to consult the advisor

Before you start implementing, stop and delegate to the `advisor` subagent whenever you are about to:

- Choose between two or more architectural options that are hard to reverse (queue vs inline, sync vs async, service boundary placement, schema shape, API contract).
- Design a parser, extractor, or transformer for messy real-world input (e.g. Romanian rebar annotations, DWG layout parsing) where the strategy — regex vs AST vs LLM fallback vs hybrid — is not obvious.
- Pick a dependency, library, or external service for a load-bearing concern (auth, storage, background jobs, PDF generation).
- Introduce a new abstraction, layer, or pattern that other code will depend on.
- Make a data modeling decision that will be annoying to migrate later.
- Handle a failure mode or edge case where the "right" behavior is a product/UX judgment call, not just a technical one.
- Commit to a Phase boundary decision (e.g. "is this still Phase 0 scope or am I sliding into Phase 1?").

### When NOT to consult the advisor

Do not delegate for:

- Straightforward implementation of an already-decided design.
- Obvious bug fixes where the cause is clear.
- Formatting, renaming, mechanical refactors.
- Questions with a single clearly correct answer.
- Exploratory reading of the codebase.

The advisor is expensive and its value comes from rarity. If you consult it for everything, you are using it wrong.

### How to consult it

1. Write a tight brief in your head: the goal, the current state, the 2–3 options you see, the specific question, and any constraints from `archyai-implementation-plan-v3.md` that are relevant.
2. Invoke the advisor subagent with that brief as the prompt. Do not dump the whole conversation — curate the context so Opus sees only what it needs.
3. Read the advisor's recommendation. You are not obligated to follow it blindly — if you disagree, say so to me (the user) and explain why, and we decide together.
4. If the advisor says "stop and clarify X", stop and ask me. Do not proceed on a guess.
5. Proceed with implementation using your normal tools.

### Reporting

When you come back from an advisor consultation, tell me in one or two sentences: what you asked, what the advisor recommended, and whether you're going to follow it. I want visibility into when Opus is being consulted and why.
