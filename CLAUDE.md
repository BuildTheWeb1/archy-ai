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
- **DWG reading**: ODA File Converter (via `ezdxf.addons.odafc`)
- **DXF parsing + rendering**: ezdxf 1.4+ (enumerates Paper Space layouts, renders to PDF)
- **PDF rendering**: matplotlib (ezdxf drawing addon backend, black-on-white A3 output)
- **Rebar parser**: Custom Python module — Phase 2 (stub exists in `parser.py`)
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
│   ├── converter.py         # ODA + ezdxf: DWG/DXF → per-layout A3 PDFs
│   ├── splitter.py          # Bundle layout PDFs into ZIP
│   ├── storage.py           # Local JSON metadata + file path helpers
│   ├── schemas.py           # Pydantic request/response models
│   │
│   ├── parser.py            # Rebar notation parser (stub) — Phase 2
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
├── sample-files/
│   ├── sample.dxf                      # Simple test drawing (1 layout)
│   └── sample_multi.dxf                # Multi-layout test drawing (5 sheets)
├── example-docs/                       # Expected output PDFs (1.pdf–17.pdf)
├── .env                                # ODA_FILE_CONVERTER path (gitignored)
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

The `.env` file at the repo root is loaded by `start-dev.sh`. For DWG support, set `ODA_FILE_CONVERTER` to the ODA binary path (auto-detected on macOS). DXF files work without ODA.

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
  1. Read DWG via ODA File Converter (or DXF directly via ezdxf)
  2. Enumerate Paper Space layouts, skip Model Space + empty layouts
  3. Render each layout → A3 PDF (black lines on white, print-ready)
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
- **Always test with `sample_multi.dxf`** after touching the converter or rendering.
- **Fail loudly on missing ODA** — if a DWG is uploaded and ODA is not installed, raise a clear error.
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

Each Paper Space layout is rendered to an A3 landscape PDF (420×297 mm) with black lines on white background (print-ready). Rendering uses ezdxf's drawing addon with a matplotlib backend.

## Implementation Phases

| Phase | Status | Goal |
|-------|--------|------|
| **1 — Layout Splitter** | **Active** | Upload DWG → download per-layout PDFs |
| 2 — Rebar Schedule | Pending | Parse annotations → Excel "Extras de armătură" |
| 3 — Auth + Billing | Pending | Clerk auth + Stripe payments |
| 4 — AI edge cases | Pending | Claude Haiku fallback for non-standard notation |

## Important

- **Rendering pipeline**: DWG → ODA File Converter → ezdxf → matplotlib → A3 PDF per layout. DXF files skip the ODA step.
- **ODA File Converter is required for DWG files**. Install from opendesignalliance.com. On macOS it auto-detects at `/Applications/ODAFileConverter.app`. DXF files work without ODA.
- **Layout names**: taken directly from the Paper Space layout tab names in the DWG/DXF. Empty layouts are skipped.
- **Uploads are ephemeral** in local dev — restart clears in-memory state but files persist on disk under `backend/uploads/`.
