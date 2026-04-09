# ArchyAI

## Project Overview

ArchyAI is a web-based SaaS for Romanian structural engineers and architects. It automates two things they currently do manually:
1. Takes an uploaded `.dwg` file and converts it to a high resolution pdf, ready to print or send to clients.

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
- **Always test with `sample_multi.dxf`** after touching the converter.
- **Fail loudly on missing APS credentials** — raise a clear error if `APS_CLIENT_ID` / `APS_CLIENT_SECRET` are not set.
- **Trace every schedule value to its source** (Phase 2: layout name + text position).

### Don't

- **Don't put business logic in route handlers** — keep them thin.
- **Don't hardcode material weights in business logic** — they live in `weights.py` only.
- **Don't add AI calls to the critical path** — AI is Phase 4 fallback for edge cases.
- **Don't use `any` in TypeScript.**
- **Don't leave `console.log` or `print()` in committed code** — use the logger.
- **Don't skip the schedule review UI step** (Phase 2) — engineers must verify before exporting.

## Important

- **Rendering pipeline**: DWG/DXF → APS Model Derivative API → combined PDF → PyMuPDF split → per-layout PDFs. No local CAD software needed.
- **APS credentials required**: Create an app at https://aps.autodesk.com/myapps and set `APS_CLIENT_ID` + `APS_CLIENT_SECRET` in `.env`.
- **Layout names**: extracted from PDF page labels. Each page corresponds to one Paper Space layout.
- **Uploads are ephemeral** in local dev — restart clears in-memory state but files persist on disk under `backend/uploads/`.
