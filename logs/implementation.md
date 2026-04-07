# Implementation Log — Archy AI

> Running log of development decisions, progress, and blockers.
> Most recent entry at the top.

---

## 2026-04-07 — Localhost demo built (Phase 1 kickoff)

### What was built

Full localhost demo covering the core value loop:
**upload DXF/DWG → extract entities → map layers to columns → export .xlsx**

#### Backend (`backend/`)
- `main.py` — FastAPI app with CORS, 5 endpoints: upload, extraction GET, layers GET, entities GET, export POST
- `extractor.py` — ezdxf-based DXF parser; extracts TEXT, MTEXT, DIMENSION, INSERT (with attributes), LWPOLYLINE, LINE, CIRCLE, ARC grouped by layer
- `exporter.py` — openpyxl xlsx export with styled headers, supports field extraction: `text`, `measurement`, `block_name`, `radius`, `area`, `attr:TAG`
- `dwg_converter.py` — DWG→DXF conversion; tries `dwg2dxf` (LibreDWG) and `ODAFileConverter` in PATH and common install locations
- Python venv at `backend/venv/`, deps: `fastapi`, `uvicorn`, `ezdxf`, `openpyxl`, `python-multipart`

#### Frontend (`frontend/`)
- Vite 6 + React 19 + TypeScript (strict)
- TanStack Router with file-based routing — 3 routes:
  - `/` — file upload (drag-and-drop)
  - `/extract/$fileId` — LayerExplorer (left) + MappingBuilder (right)
  - `/preview/$fileId` — DataPreview table + Export button
- TanStack Query for all API calls (`useUpload`, `useExtraction`, `useLayers`, `useExport`)
- Tailwind CSS v4 via `@tailwindcss/vite`
- Mappings passed between extract → preview routes via `sessionStorage` (keyed by `fileId`)

#### Sample files
- `sample-files/sample.dxf` — 7 layers, 60 entities; covers all extractable entity types:
  - `S-BEAM` (LINE + TEXT — beam IDs and cross-sections)
  - `S-COL` (INSERT with ID/SIZE attributes — column schedule)
  - `S-WALL` (LWPOLYLINE)
  - `S-DOOR` (INSERT with TAG/ROOM attributes)
  - `S-STAIR` (LWPOLYLINE + TEXT)
  - `ANNOTATION` (TEXT + MTEXT — notes, project info)
  - `DIMENSIONS` (DIMENSION entities)
- `sample-files/generate_sample.py` — regenerate the sample at any time

### Decisions made

| Decision | Rationale |
|---|---|
| No database / no auth | Phase 1 only — in-memory store, fastest path to user validation |
| TanStack Router from day 1 | Requested by Claudiu — avoids refactor cost later |
| Vite 6 (not 8) | Node 20.18.1 was installed; Vite 8 requires 20.19+. Downgraded rather than force an upgrade. Node 22 installed in parallel for future use. |
| `sessionStorage` for mappings | Simplest cross-route state without adding a global store; scoped per file |
| Mappings per layer+type (not per layer) | Allows multiple columns from same layer (e.g. TEXT + INSERT both from S-BEAM) |
| `plain_text()` not `plain_mtext()` | `plain_mtext()` removed in ezdxf 1.4; `plain_text()` is the current API |

### Blockers / pending

- **DWG conversion not working** — LibreDWG not available as a Homebrew formula; ODA File Converter not installed. Code is ready in `dwg_converter.py`. User needs to install ODA File Converter from opendesign.com.
- **No real DXF test files** — only a synthetic sample and a `.dwg` in `example-docs/`. First real-world validation needed.
- **Mapping templates not persisted** — mappings live in `sessionStorage` only; lost on page refresh or new session. Phase 2 will add DB persistence.

### Next steps (Phase 1 remaining)

- [ ] Install ODA File Converter and test with `example-docs/newmoda (1).dwg`
- [ ] Validate extraction output with a real architect / show the demo
- [ ] Document: what data is useful, what's noise, top 3 extraction patterns
- [ ] Decide: proceed to Phase 2 MVP or pivot

---

## 2026-04-07 — Project initialised

- Repository created at `archy-ai/`
- Implementation plan written (`cad-extract-implementation-plan.pdf`)
- CLAUDE.md project instructions added
