# Archy AI — CAD Extract

> Extract structured data from DWG/DXF files and export to Excel or Google Sheets.
> Built for construction firms and architecture practices.

---

## What it does

Upload an AutoCAD drawing → see every layer and entity type extracted → map layers to spreadsheet columns → export a clean `.xlsx` in one click. Reusable mapping templates eliminate repeat work across drawing sets.

## Current status

**Phase 1 — Localhost demo** (active)
Core extraction loop works end-to-end on DXF files. DWG support ready pending ODA File Converter install. No auth, no cloud, no database — in-memory state for rapid validation.

See [`logs/implementation.md`](logs/implementation.md) for a full development log.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite 6 |
| Routing | TanStack Router (file-based) |
| Server state | TanStack Query |
| Styling | Tailwind CSS v4 |
| Backend | Python 3.12+ + FastAPI |
| DXF parsing | ezdxf |
| DWG conversion | ODA File Converter / LibreDWG |
| Export | openpyxl (.xlsx) |

---

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 20.19+ (or 22+)
- pnpm

### First-time setup

```bash
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
# From the project root — starts both servers
./start-dev.sh
```

| Service | URL |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

### Test with sample file

A synthetic structural DXF is included:

```bash
# upload via curl
curl -X POST http://localhost:8000/api/upload \
  -F "file=@sample-files/sample.dxf"
```

Or drag-and-drop it in the UI.

---

## DWG support

DWG files require a converter. Install one of:

**Option A — ODA File Converter** (recommended, free)
1. Download from opendesign.com → Guest files → ODA File Converter
2. Install to `/Applications/ODAFileConverter/`
3. Restart the backend — DWG uploads will work automatically

**Option B — LibreDWG**
```bash
# Build from source: https://www.gnu.org/software/libredwg/
# Once dwg2dxf is in PATH, it will be picked up automatically
```

---

## Project structure

```
archy-ai/
├── backend/
│   ├── main.py           # FastAPI app + all route handlers
│   ├── extractor.py      # ezdxf DXF parsing → structured JSON
│   ├── exporter.py       # openpyxl .xlsx export
│   ├── dwg_converter.py  # DWG→DXF via ODA or LibreDWG
│   ├── requirements.txt
│   └── uploads/          # temp file storage (gitignored)
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx
│   │   │   ├── index.tsx              # / — upload
│   │   │   ├── extract/$fileId.tsx   # layer explorer + mapping builder
│   │   │   └── preview/$fileId.tsx   # data preview + export
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── LayerExplorer.tsx
│   │   │   ├── MappingBuilder.tsx
│   │   │   └── DataPreview.tsx
│   │   ├── hooks/useExtraction.ts
│   │   └── types.ts
│   ├── vite.config.ts
│   └── package.json
├── sample-files/
│   ├── sample.dxf             # synthetic structural drawing (7 layers, 60 entities)
│   └── generate_sample.py     # script to regenerate
├── logs/
│   └── implementation.md      # development log
├── start-dev.sh               # starts backend + frontend
└── cad-extract-implementation-plan.pdf
```

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload DXF/DWG, returns `file_id` |
| `GET` | `/api/extractions/{id}` | Full extraction result |
| `GET` | `/api/extractions/{id}/layers` | Layer summary (types + counts) |
| `GET` | `/api/extractions/{id}/entities/{layer}` | Entities for a specific layer |
| `POST` | `/api/extractions/{id}/export` | Export mapped data as `.xlsx` |
| `GET` | `/health` | Health check |

---

## Roadmap

| Phase | Status |
|---|---|
| Phase 1 — PoC: CLI + localhost demo | **In progress** |
| Phase 2 — MVP: auth, DB, cloud storage, Google Sheets | Planned |
| Phase 3 — Beta: orgs, templates, billing | Planned |
| Phase 4 — Growth: ML auto-mapping, BIM/IFC | Planned |

See [`cad-extract-implementation-plan.pdf`](cad-extract-implementation-plan.pdf) for the full plan.
