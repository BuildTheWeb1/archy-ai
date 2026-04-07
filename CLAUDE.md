# ArchyAI

## Project Overview

ArchyAI is a web-based SaaS for Romanian structural engineers and architects. It automates two things they currently do manually:

1. **Layout Splitter (Feature 1 — active)**: Takes an uploaded `.dwg` file and exports each AutoCAD Layout (Paper Space tab) as a separate A3 PDF, ready to print or send to clients.
2. **Rebar Schedule Generator (Feature 2 — Phase 2)**: Parses rebar annotations across the project layouts, aggregates marks, computes total lengths and weights, and produces an Excel file matching the Romanian "Extras de armătură" standard.

Target users: Romanian structural engineering firms (1–20 people). They currently split layouts by hand in AutoCAD and produce rebar schedules manually in 2–4 hours per project.

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
- **DWG → PDF conversion**: CloudConvert API (native CAD rendering, one page per layout)
- **PDF splitting**: pypdf (splits multi-page PDF into per-layout PDFs)
- **Rebar parser**: Custom Python module — Phase 2 (stub exists in `parser.py`)
- **DXF parsing**: ezdxf 1.4+ — Phase 2 only (rebar text extraction)
- **Excel export**: openpyxl — Phase 2 only
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
│   ├── converter.py         # CloudConvert DWG → multi-page PDF
│   ├── splitter.py          # Split multi-page PDF into per-layout PDFs
│   ├── storage.py           # Local JSON metadata + file path helpers
│   ├── schemas.py           # Pydantic request/response models
│   │
│   ├── parser.py            # Rebar notation parser (stub) — Phase 2
│   ├── weights.py           # Material weight constants (kg/m by diameter)
│   │
│   ├── uploads/             # Runtime storage — gitignored
│   │   └── {drawing_id}/
│   │       ├── metadata.json
│   │       ├── original.dwg
│   │       ├── converted.pdf
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
├── sample-files/
│   └── newmoda.dwg                     # Real test drawing
├── example-docs/                       # Expected output PDFs (1.pdf–17.pdf)
├── .env                                # CLOUDCONVERT_API_KEY (gitignored)
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

The `.env` file at the repo root is loaded by `start-dev.sh`. It must contain `CLOUDCONVERT_API_KEY`.

## API Endpoints

```
POST  /api/drawings/upload              Upload DWG → triggers background conversion
GET   /api/drawings/{id}                Poll status: processing | ready | error
GET   /api/drawings/{id}/layouts/{n}/pdf  Download single layout PDF
GET   /api/drawings/{id}/download       Download ZIP of all layouts
GET   /health
```

## Processing Pipeline

```
User uploads .dwg
      ↓
POST /api/drawings/upload
  → saves file to uploads/{id}/original.dwg
  → sets status = "processing"
  → returns {id, status: "processing"} immediately
      ↓
Background task (_process_drawing):
  1. CloudConvert: original.dwg → converted.pdf  (1 page per AutoCAD layout)
  2. pypdf split:  converted.pdf → layouts/0.pdf, layouts/1.pdf, …
  3. Extract layout names from PDF bookmarks (or fallback: "Layout_N")
  4. Update metadata.json: status = "ready", layouts = [{index, name}]
      ↓
Frontend polls GET /api/drawings/{id} every 2s
  → When status = "ready": shows layout list with download buttons
```

## Development Guidelines

### Do

- **Keep route handlers thin** — delegate all logic to `converter.py`, `splitter.py`, etc.
- **Use Pydantic schemas** for all FastAPI request/response bodies.
- **Use TypeScript strict mode** — no `any`.
- **Always test with `newmoda.dwg`** after touching the converter or splitter.
- **Fail loudly on missing API key** — never silently fall back to lower-quality rendering.
- **Trace every schedule value to its source** (Phase 2: layout name + text position).

### Don't

- **Don't put business logic in route handlers** — keep them thin.
- **Don't hardcode material weights in business logic** — they live in `weights.py` only.
- **Don't add AI calls to the critical path** — AI is Phase 4 fallback for edge cases.
- **Don't use `any` in TypeScript.**
- **Don't leave `console.log` or `print()` in committed code** — use the logger.
- **Don't skip the schedule review UI step** (Phase 2) — engineers must verify before exporting.

## Domain Rules

### Romanian Rebar Notation (Phase 2)

The parser must recognise both Latin `Ø` and Cyrillic `Ф` as diameter symbols. They appear interchangeably in real drawings. Treat them as equivalent.

### Material Weight Constants

Defined in `backend/weights.py` — never hardcoded elsewhere:

```python
REBAR_WEIGHTS_KG_PER_M = {
    6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888, 14: 1.210,
    16: 1.580, 18: 2.000, 20: 2.470, 22: 2.984, 25: 3.853,
}
```

### Schedule Format (Phase 2)

Excel columns in this exact order:
```
Marca | Ø [mm] | Oțel | Buc. | Lung. [m] | Lung./Ø [m] | Masa Ø/m [kg/m] | Masa/Ø [kg] | Masa totală [kg]
```

### A3 Output

All layout PDFs come from CloudConvert, which preserves the AutoCAD paper space size. The result is native-quality PDF matching AutoCAD's own export.

## Implementation Phases

| Phase | Status | Goal |
|-------|--------|------|
| **1 — Layout Splitter** | **Active** | Upload DWG → download per-layout PDFs |
| 2 — Rebar Schedule | Pending | Parse annotations → Excel "Extras de armătură" |
| 3 — Auth + Billing | Pending | Clerk auth + Stripe payments |
| 4 — AI edge cases | Pending | Claude Haiku fallback for non-standard notation |

## Important

- **Phase 0 validated**: the core DWG → PDF pipeline works via CloudConvert. The previous ezdxf+matplotlib rendering is gone.
- **CloudConvert API key is required**. Without it the backend fails with a clear error. Key is in `.env`.
- **Layout names**: extracted from PDF bookmarks when available (AutoCAD embeds them). Fallback: `Layout_N`.
- **Uploads are ephemeral** in local dev — restart clears in-memory state but files persist on disk under `backend/uploads/`.
