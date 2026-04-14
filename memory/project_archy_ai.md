---
name: Archy AI project state
description: Current product direction, stack decisions, and how to start the dev server
type: project
---

ArchyAI has pivoted from DWG→PDF conversion (APS was not obtainable) to a **PDF → Romanian rebar schedule ("Extras de armătură") extractor**.

**Product**: Upload PDFs exported from AutoCAD → extract rebar marks via regex pipeline → review/edit schedule grid → export to Excel (.xlsx).

**Stack (no changes from plan except auth deferred)**:
- Backend: Python 3.12 + FastAPI + pdfplumber + openpyxl + PyMuPDF
- Frontend: React 19 + TypeScript + Vite + TanStack Router/Query + TailwindCSS
- Storage: local filesystem (no Supabase yet) — `backend/uploads/{project_id}/`
- Auth: **not implemented yet** — all endpoints are open

**Backend pipeline** (in `backend/pipeline/`):
- `models.py` — RebarMark, ScheduleRow dataclasses
- `extractor.py` — pdfplumber text/table extraction
- `parser.py` — regex patterns (Ø/Ф both supported), `parse_rebar_label`, `parse_embedded_schedule`
- `rotated.py` — reconstruct text from rotated chars
- `aggregator.py` — group marks by number, detect inconsistencies
- `weights.py` — kg/m constants, build_schedule_row
- `excel_export.py` — openpyxl writer (Romanian "Extras de armătură" format)
- `orchestrator.py` — run_pipeline(pdf_paths) → (rows, warnings)

**API routes** (all open, no JWT):
- `POST/GET /api/projects` — CRUD
- `POST /api/projects/{id}/pdfs` — upload up to 10 PDFs
- `POST /api/projects/{id}/extract` → background task
- `GET/PUT /api/projects/{id}/schedule` — get/edit rows
- `GET /api/projects/{id}/schedule/xlsx` — download Excel

**Frontend routes**:
- `/` — Projects list (create, delete, navigate)
- `/projects/$projectId` — Upload PDFs, trigger extraction, edit schedule table, export Excel

**How to start**:
```bash
./start-dev.sh
# or manually:
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
cd frontend && pnpm dev
```

**Why:** APS (Autodesk Platform Services) model derivative API was not accessible. The rebar schedule extractor is the primary product value for Romanian structural engineers.

**How to apply:** Any future work builds on this pipeline. Auth (Clerk) is the next phase.
