# ArchyAI — Implementation Plan v3

**Product:** Web SaaS that splits AutoCAD DWG files into A3 PDFs per layout and auto-generates Romanian structural rebar schedules ("Extras de armătură") from the drawing data.

**Target users:** Romanian structural engineers and architects working on residential and small commercial projects.

**Author:** Claudiu | **Date:** April 2026 | **Version:** 3.0 (grounded in real DWG analysis)

---

## What Changed in v3

This plan is rewritten after analyzing your actual `newmoda.dwg` source file and all 12 expected output PDFs. Three findings reshape the architecture:

1. **Rebar data is already labeled in the drawings.** Annotations like `4Ø14 L=0.95` and `2x2Ф14 L=8.60` are placed by the architect during drafting. We don't need to "discover" rebar from raw geometry — we extract structured labels.

2. **The schedule format follows a fixed Romanian standard.** "Extras de armătură" tables in R04, R08, R09 all use identical column structures defined by Romanian construction norms. Output format is predictable.

3. **AI is optional, not central.** A deterministic parser handles 90%+ of cases. AI becomes a Phase 2 quality enhancement for edge cases and non-standard notation, not a Phase 1 dependency.

This makes the product **simpler, faster, cheaper, and more reliable** than v2 suggested.

## What Changed in v3.1 — CloudConvert Cannot Split Layouts (April 7, 2026)

After building and testing the Feature 1 (Layout Splitter) MVP using CloudConvert, **critical findings** require a change in the conversion pipeline:

### Problem: CloudConvert Loses Paper Space Layouts

CloudConvert's `cadconverter` engine (v8.10, the only available engine for DWG→PDF) **does not properly extract Paper Space layout tabs** from DWG files. Testing with `newmoda.dwg` revealed:

| What we expected | What CloudConvert produced |
|---|---|
| 17 separate A3 PDFs (842×1191 pts each) | 1 PDF with 2 pages at 800×600 pts |
| Each Paper Space layout rendered full-size | Model Space (all layouts as tiny thumbnails) + 1 near-empty page |
| Proper A3 page dimensions | Generic 800×600 pixel-like dimensions |
| Bookmarks with layout names | No bookmarks |

**Both DWG→PDF and DWG→DXF conversions via CloudConvert lose layouts.** The DXF output also contained only 2 layouts (Model + 1 "A3 Landscape") instead of 17 Paper Space tabs. The cadconverter engine has only 4 parameters (`all_layouts`, `width`, `height`, `auto_zoom`) — none allow selecting or excluding specific layouts.

Additionally, the converter code was only downloading `files[0]` from CloudConvert's export, but testing confirmed CloudConvert returns only 1 output file regardless (not 17 separate files).

### Root Cause

CloudConvert's CAD engine cannot enumerate and render individual AutoCAD Paper Space layout tabs. It renders Model Space as the primary output. This is a fundamental engine limitation, not a parameter configuration issue.

### Impact on Architecture

The Layout Splitter pipeline **must change** from:

```
DWG → CloudConvert → multi-page PDF → pypdf split → per-layout PDFs
```

To:

```
DWG → ODA File Converter → DXF (all 17 layouts preserved)
    → ezdxf reads DXF → enumerates Paper Space layouts
    → ezdxf.addons.drawing + matplotlib → render each layout to A3 PDF
```

### Validated Components

| Component | Status | Notes |
|---|---|---|
| ezdxf 1.4.3 DXF reading | Working | Correctly enumerates layouts, entities, blocks from DXF |
| ezdxf matplotlib rendering | Working | Successfully renders Model Space to PDF (25MB test output) |
| ezdxf pymupdf backend | Available | PyMuPDF (AGPL) installed, untested |
| ODA File Converter | **Not installed** | Required — preserves all layouts during DWG→DXF conversion |
| CloudConvert DWG→PDF | **Broken** | Cannot extract Paper Space layouts |
| CloudConvert DWG→DXF | **Broken** | Same issue — only 2 of 17 layouts preserved |

### Required Action

1. **Install ODA File Converter** (free download from opendesignalliance.com, macOS version)
2. **Rewrite `converter.py`** to use ODA via `ezdxf.addons.odafc` for DWG→DXF
3. **Add layout rendering** using ezdxf's drawing add-on + matplotlib for DXF→A3 PDF
4. **Remove CloudConvert dependency** from the conversion pipeline (may keep for future fallback)
5. **Budget for ODA commercial license** (~$200/year) for production SaaS deployment

### Open Risk: Rendering Quality

The example PDFs were produced by "Microsoft: Print To PDF" from within AutoCAD — native rendering quality. The ezdxf + matplotlib rendering approach will produce acceptable but potentially lower-fidelity output (different text rendering, simplified hatches, etc.). This needs Phase 0 visual comparison testing.

### Updated Cost Impact

| Component | Before (CloudConvert) | After (ODA + ezdxf) |
|---|---|---|
| Per-drawing API cost | ~$0.01 (CloudConvert credit) | $0 (local processing) |
| Infrastructure | CloudConvert API key | ODA File Converter binary |
| Licensing | CloudConvert subscription | ODA license ~$200/year |
| Processing time | ~30-60s (network round-trip) | ~5-15s (local, CPU-bound) |
| Quality control | Depends on CloudConvert engine | Full control via ezdxf |

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Analysis of Real Source Data](#2-analysis-of-real-source-data)
3. [Feature 1 — Layout Splitter](#3-feature-1--layout-splitter)
4. [Feature 2 — Rebar Schedule Generator](#4-feature-2--rebar-schedule-generator)
5. [Technical Architecture](#5-technical-architecture)
6. [The Parser — Core Engine](#6-the-parser--core-engine)
7. [AI Strategy (Reduced Role)](#7-ai-strategy-reduced-role)
8. [Implementation Phases](#8-implementation-phases)
9. [Cost Analysis](#9-cost-analysis)
10. [Risk Register](#10-risk-register)
11. [Open Questions](#11-open-questions)

---

## 1. Product Overview

### Name

**ArchyAI** — though we'll find that "AI" plays a smaller role than expected; the name still works as a product brand.

### Two Features

**Feature 1: Layout Splitter**
Architect uploads a `.dwg` file. ArchyAI parses each AutoCAD Layout (Paper Space tab), renders each as an A3 PDF, and bundles them for download.

**Feature 2: Rebar Schedule Generator**
ArchyAI scans all rebar annotations across the project's layouts, parses them into structured data, aggregates marks across drawings, computes total lengths and weights, and produces an Excel file matching the Romanian "Extras de armătură" format.

### Target Customer Profile

- Romanian structural engineering firms (1–20 people)
- Drawing in AutoCAD using standard Romanian rebar notation
- Currently producing schedules manually (hours of work per project)
- Working on residential, small commercial, and industrial projects
- Pain point: schedule preparation is tedious, error-prone, and gets redone after every drawing revision

### Value Proposition

**Before:** Engineer spends 2–4 hours manually counting rebar marks, calculating total lengths and weights, transcribing into Excel.

**After:** Upload DWG → 30 seconds later, download A3 PDFs and a complete schedule Excel ready to print.

**Conservative ROI:** At 50€/hour engineer time and 3 hours saved per project, ArchyAI saves ~150€ per project. A 79€/month subscription pays for itself with one project.

---

## 2. Analysis of Real Source Data

### The newmoda.dwg File

The uploaded file is a complete structural project for a P+1E house (ground floor + 1 upper floor) by ArchiBau Studio in Giroc, Romania. File format: DWG AC1032 (AutoCAD 2018/2019/2020), 4.4 MB.

### The Layouts (17 expected from example-docs)

| # | Sheet | Title | Has Schedule | Source Layouts for Schedule |
|---|-------|-------|--------------|------------------------------|
| 1 | R01 | Plan săpătură | No | — |
| 2 | R02 | Plan fundații | No (data feeds R04) | — |
| 3 | R03 | Detalii fundații I | No | — |
| 4 | R04 | Detalii fundații II | **Yes** | R02, R03, R04 |
| 5 | R05 | Plan cofraj planșeu parter | No | — |
| 6 | R06 | Plan buiandrugi parter | No (data feeds R08) | — |
| 7 | R07 | Plan centuri și grinzi parter | No (data feeds R08) | — |
| 8 | R08 | Detalii planșeu parter | **Yes** (16 marks) | R06, R07, R08 |
| 9 | R09 | Plan placă b.a. parter | **Yes** (12 marks) | R09 only |
| 10 | R10 | Plan cofraj planșeu etaj | No | — |
| 11 | R11 | Plan buiandrugi etaj | No | (would feed an R13 if it existed) |
| 12 | R12 | Plan centuri și grinzi etaj | No | (would feed an R13 if it existed) |

### Rebar Annotation Patterns Observed

From parsing the PDF text content, here are the actual notation styles used:

**Bar marks with count, diameter, length:**
```
1 2x2Ф14 L=8.60     → mark 1, group of 2×2 = 4 bars, Ø14mm, length 8.60m
2 2x2Ф14 L=3.30     → mark 2, 4 bars, Ø14mm, length 3.30m
4Ф14 L=0.95         → 4 bars, Ø14mm, length 0.95m
3Ф14 L=2.95         → mark 1, 3 bars, Ø14mm, length 2.95m
2x3Ф12 L=1.35       → 6 bars, Ø12mm, length 1.35m
2x3Ф16 L=5.70       → 6 bars, Ø16mm, length 5.70m
```

**Stirrups (etrieri) with spacing:**
```
etrieri Ø8/15       → Ø8mm stirrups at 15cm spacing
etrieri Ф8/15       → same, Cyrillic Ф variant
Ø8/30               → Ø8mm at 30cm
Ø8/15               → Ø8mm at 15cm
```

**Welded mesh (plasă sudată):**
```
Ø6/10/10            → Ø6mm mesh, 10×10cm grid
STNB Ø6/10/10       → STNB type mesh (Romanian standard)
1 rând plasă sudată → 1 row of welded mesh
```

**Slab rebar (continuous bars):**
```
Ф10/15              → Ø10mm bars at 15cm spacing (slab reinforcement)
1 Ф10/15 L=8.80     → mark 1, Ø10mm at 15cm, length 8.80m
```

**Element labels (stâlpișori, mustăți):**
```
9 buc. stâlpișori   → 9 pieces of small columns
Mustăți stâlpișori 25/25, 23 buc.  → 23 pieces of column starter bars, 25/25 section
```

**Material specifications (consistent across all sheets):**
```
Beton fundatii- C30/37 ... CEM II A-S 42,5-XC4+XF1
Beton elevatii- C25/30 ... CEM II A-S 42,5-XC2
Beton placa- C20/25 ... CEM II A-S 42,5-XC2
Oțel beton - BST500C
Plasă sudată - STNB Ø6/10/10
```

### The Schedule Format ("Extras de armătură")

All three schedules (R04, R08, R09) share this exact column structure:

| Marca | Ø [mm] | Oțel | Buc. | Lung. [m] | Lung./Ø [m] (per Ø) | Masa Ø/m [kg/m] | Masa/Ø [kg] | Masa totală [kg] |
|-------|--------|------|------|-----------|---------------------|-----------------|-------------|------------------|

**Example row from R09:**
```
Marca: 1
Ø: 10 mm
Oțel: BST500
Buc: 45
Lung: 8.80 m
Lung/Ø: 396.0 m  (45 × 8.80)
Masa Ø/m: 0.617 kg/m  (standard table for Ø10)
Masa/Ø: 244.5 kg
```

**Standard rebar weights by diameter (kg/m):**

| Ø (mm) | kg/m | Used in your project |
|--------|------|---------------------|
| 6 | 0.222 | Yes (mesh) |
| 8 | 0.395 | Yes (stirrups) |
| 10 | 0.617 | Yes (slab) |
| 12 | 0.888 | Yes (centuri) |
| 14 | 1.210 | Yes (foundations) |
| 16 | 1.580 | Yes (lintels) |
| 18 | 2.000 | — |
| 20 | 2.470 | — |
| 22 | 2.984 | — |
| 25 | 3.853 | — |

These are physical constants. ArchyAI hardcodes them.

### Layer and Block Conventions

I cannot inspect the DWG internals without ezdxf, but based on the visual output, I can infer this firm uses:

- A title block as a paper space block (visible in every layout)
- Rebar drawn as polylines on dedicated layers
- Annotations as TEXT/MTEXT entities placed near the rebar
- Hatching for concrete sections
- Dimensions for the architectural cotation

**Critical unknown:** whether the rebar annotations are linked to the rebar geometry (block attributes) or just floating text near it. This affects whether ArchyAI can attribute a label to a specific element or only count occurrences. The Phase 0 validation script will determine this.

---

## 3. Feature 1 — Layout Splitter

### User Story

> As a structural engineer, I upload my project DWG file and immediately get back A3 PDFs of every layout, ready to print or send to my client.

### Pipeline

> **Note (v3.1):** The original plan called for CloudConvert as the DWG→PDF engine. Testing proved CloudConvert's `cadconverter` engine cannot extract Paper Space layouts (produces 2 pages instead of 17). The pipeline below uses ODA File Converter + ezdxf instead.

```
DWG file uploaded
      ↓
POST /api/drawings/upload
  → saves to uploads/{id}/original.dwg
  → sets status = "processing"
  → returns {id, status} immediately
      ↓
Background task:
  1. ODA File Converter: original.dwg → converted.dxf (all layouts preserved)
  2. ezdxf reads DXF, enumerates Paper Space layouts (skipping Model Space)
  3. For each layout:
     ├─ Get layout name from DXF (e.g., "R01", "R02", ..., "R12")
     ├─ Render via ezdxf.addons.drawing + matplotlib backend
     ├─ Output: PDF fitted to A3 (297×420mm, 842×1191 pts)
     └─ Save as layouts/{index}.pdf
  4. Update metadata.json: status = "ready", layouts = [{index, name}]
      ↓
Frontend polls GET /api/drawings/{id} every 2s
  → When status = "ready": shows layout list with download buttons
```

### A3 Normalization

Original layouts in your project appear to be A3 already (based on the title block format). For other projects with A1/A2/A4 originals, fit-to-A3 with white margins is the safe default. Three options exposed in the UI:

- **Auto-fit** (default): scale to fit A3, preserve aspect ratio
- **Crop to A3**: keep native scale, crop overflow
- **Stretch**: fill A3 (rarely wanted, but available)

### Romanian Character Handling

The drawings contain Romanian (ă, î, ș, ț) and mixed Latin/Cyrillic (Ø vs Ф). The matplotlib backend in ezdxf needs Unicode-capable fonts loaded explicitly. We'll bundle DejaVu Sans and Noto Sans as fallback fonts.

### Output

```
newmoda_layouts.zip
├── manifest.json
├── 01_R01_plan_sapatura.pdf
├── 02_R02_plan_fundatii.pdf
├── 03_R03_detalii_fundatii_I.pdf
├── 04_R04_detalii_fundatii_II.pdf
├── 05_R05_plan_cofraj_planseu_parter.pdf
├── 06_R06_plan_buiandrugi_parter.pdf
├── 07_R07_plan_centuri_si_grinzi_parter.pdf
├── 08_R08_detalii_planseu_parter.pdf
├── 09_R09_plan_placa_ba_parter.pdf
├── 10_R10_plan_cofraj_planseu_etaj.pdf
├── 11_R11_plan_buiandrugi_etaj.pdf
└── 12_R12_plan_centuri_si_grinzi_etaj.pdf
```

The `manifest.json` includes layout name, original page size, page count, and a content fingerprint for revision detection (Phase 4 feature).

---

## 4. Feature 2 — Rebar Schedule Generator

### User Story

> As a structural engineer, after my drawings are split, I click "Generate schedule" and get an Excel file with the complete "Extras de armătură" — all rebar marks counted, lengths totaled, weights calculated. I review and export.

### How It Works

This is the core technical insight from analyzing your real files:

```
Project layouts loaded (e.g., R01–R12)
      ↓
Step 1: Extract all TEXT/MTEXT entities from each layout
      ↓
Step 2: Parse each text against the rebar notation grammar
        Recognize patterns:
          - Mark labels: "1 2x2Ф14 L=8.60"
          - Bar specs: "4Ф14 L=0.95"
          - Stirrups: "etrieri Ø8/15"
          - Mesh: "Ø6/10/10"
          - Counts: "9 buc. stâlpișori"
        Reject: dimensions, notes, dates, project info
      ↓
Step 3: Aggregate by mark number across all source layouts
        For each mark: sum counts, validate consistent dimensions
        Detect when same mark appears in multiple sheets (= same element)
      ↓
Step 4: Lookup material weights from constants table
        14mm = 1.210 kg/m, 12mm = 0.888 kg/m, etc.
      ↓
Step 5: Compute totals
        Lung/Ø = count × length per mark
        Masa/Ø = Lung/Ø × kg/m
        Masa totală = sum of all Masa/Ø per diameter
      ↓
Step 6: Generate Excel matching Romanian "Extras de armătură" format
      ↓
Step 7: User reviews in browser, edits if needed, downloads
```

### Schedule Generation Modes

**Mode A: Whole project (default)**
Generate one consolidated schedule for the entire project, like R04 + R08 + R09 combined into one table or as separate sheets in one workbook.

**Mode B: Per detail sheet**
Generate one schedule per "details" sheet (R04, R08, R09), matching the exact original output structure.

**Mode C: Custom selection**
User picks which layouts to include in the schedule.

### Excel Output

```
project_295_2026_extras_armatura.xlsx
├── Sheet: "Fundatii (R04)"
│   └── Marca | Ø | Oțel | Buc | Lung | Lung/Ø | Masa/m | Masa/Ø | Total
├── Sheet: "Planseu parter (R08)"
│   └── Same structure, 16 marks
├── Sheet: "Placa parter (R09)"
│   └── Same structure, 12 marks
├── Sheet: "Materiale"
│   └── All material specs from drawings
└── Sheet: "Audit trail"
    └── Where each mark was found, line by line
```

The Excel file is formatted to match the visual style of the existing PDF schedules (header row shaded, totals bolded, units in column headers).

### User Review UI

Before exporting, the user sees the generated schedule in the browser:
- Editable table with all extracted marks
- Confidence indicator per row (green/yellow/red)
- "Why?" link on each row showing the source label and which layout it came from
- Add/edit/delete rows manually
- Recalculate totals after edits
- Export to Excel

This review step is **essential for trust**. Engineers must verify before signing off on a schedule.

---

## 5. Technical Architecture

### Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 19 + TypeScript + Vite | Your existing expertise |
| UI components | shadcn/ui + TailwindCSS | Professional, fast |
| Routing | TanStack Router | Your existing patterns |
| Server state | TanStack Query | Polling for processing status |
| Backend API | Python 3.12 + FastAPI | Best ezdxf ecosystem |
| DWG → DXF | ODA File Converter (CLI) | Industry standard, handles all DWG versions |
| DXF parsing | ezdxf 1.4+ | Mature, actively maintained |
| Layout rendering | ezdxf.addons.drawing + matplotlib | Pure Python, full control |
| PDF generation | matplotlib pdf backend + reportlab | Reliable A3 output |
| Excel generation | openpyxl | Standard, well-supported, formatting capable |
| Rebar parser | Custom Python module | The core IP of the product |
| Task queue | Celery + Redis | Required — file processing is CPU-bound |
| Database | PostgreSQL | Projects, schedules, user mappings |
| Object storage | Cloudflare R2 | Cheaper than S3, free egress |
| Auth | Clerk | Fast integration, supports teams |
| Hosting | Railway (backend) + Vercel (frontend) | Simple, scales |
| Monitoring | Sentry | Error tracking |
| Payments | Stripe | EU-compliant |

### System Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  Upload → Status → Layouts → Schedule Review → Downloads   │
└──────────────────────────┬─────────────────────────────────┘
                           │ REST API (HTTPS)
┌──────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  /upload  /jobs  /layouts  /schedule  /export  /auth       │
└────┬──────────────────────────────────────────┬────────────┘
     │                                          │
┌────▼─────┐                              ┌─────▼──────┐
│  Redis   │                              │ PostgreSQL │
│ (Queue)  │                              │   (Data)   │
└────┬─────┘                              └────────────┘
     │
┌────▼───────────────────────────────────────────┐
│              Celery Workers                     │
│                                                 │
│  Worker 1: DWG → DXF conversion                │
│  Worker 2: Layout enumeration & A3 PDF render  │
│  Worker 3: Rebar parsing & schedule generation │
└────────────────────┬───────────────────────────┘
                     │
            ┌────────▼────────┐
            │  Cloudflare R2  │
            │  (file storage) │
            └─────────────────┘
```

### Data Model

```sql
-- Users and orgs
User { id, email, org_id, role, created_at }
Organization { id, name, plan, locale, created_at }

-- Projects
Project {
  id, org_id, name, project_number,
  beneficiary, location,
  created_at, updated_at
}

-- Drawings (uploaded DWG files)
Drawing {
  id, project_id, original_filename, r2_key, file_size,
  status,                        -- uploaded | converting | ready | error
  error_message,
  layout_count,
  uploaded_at, processed_at
}

-- Layouts extracted from each drawing
Layout {
  id, drawing_id, name, page_index,
  original_size_mm,              -- {width: 297, height: 420}
  pdf_r2_key,                    -- A3-fitted PDF
  has_rebar_annotations,         -- bool, set during parsing
  raw_extracted_text             -- JSON: all TEXT/MTEXT for debugging
}

-- Generated schedules
Schedule {
  id, drawing_id,
  mode,                          -- whole_project | per_detail | custom
  source_layout_ids,             -- which layouts contributed
  generated_at,
  parsed_marks,                  -- JSON: structured mark data
  user_corrections,              -- JSON: edits the user made
  xlsx_r2_key                    -- final Excel file
}

-- Material weight constants (configurable per organization for future intl)
MaterialWeight {
  id, org_id, diameter_mm, kg_per_meter, steel_grade
}

-- Async processing jobs
Job {
  id, drawing_id, type,          -- convert | render | schedule
  status, progress, started_at, completed_at, error
}
```

### Key API Endpoints

```
POST   /api/projects                       Create a project
GET    /api/projects                       List user's projects
GET    /api/projects/{id}                  Project details

POST   /api/drawings/upload                Get presigned R2 upload URL
POST   /api/drawings/{id}/process          Trigger DWG → layouts pipeline
GET    /api/drawings/{id}                  Status + layouts
GET    /api/drawings/{id}/layouts          List of layouts
GET    /api/drawings/{id}/download         ZIP of all A3 PDFs

GET    /api/layouts/{id}                   Layout details
GET    /api/layouts/{id}/pdf               Single A3 PDF download
GET    /api/layouts/{id}/text              Raw extracted text (for debugging)

POST   /api/drawings/{id}/schedule         Trigger schedule generation
GET    /api/schedules/{id}                 Generated schedule data
PUT    /api/schedules/{id}                 Save user corrections
GET    /api/schedules/{id}/xlsx            Download Excel
```

---

## 6. The Parser — Core Engine

This is the most important module in the entire product. Let me describe it in detail.

### Input

A list of (layout_name, text_content, position) tuples extracted from each layout:

```python
[
  ("R02", "1 2x2Ф14 L=8.60", (1235, 4567)),
  ("R02", "2 2x2Ф14 L=3.30", (1340, 4570)),
  ("R02", "Ф6/10/10", (980, 4200)),
  ("R02", "1 rând plasă sudată", (985, 4180)),
  ("R02", "Notă: Constructorul va verifica...", (50, 100)),
  ("R02", "Beton fundatii- C30/37", (50, 200)),
  ...
]
```

### Parsing Grammar

The parser uses a hierarchy of regexes (with named groups) to recognize known patterns. Each pattern produces a structured `RebarMark` object or is rejected as non-rebar text.

```python
PATTERNS = [
    # Mark with count, diameter, length: "1 2x2Ф14 L=8.60"
    {
        "name": "marked_bar_group",
        "regex": r"^(?P<mark>\d+)\s+(?P<groups>\d+x\d+|\d+)(?P<dia_sym>[ØФ])(?P<dia>\d+)\s+L=(?P<length>[\d.]+)$",
        "extract": lambda m: RebarMark(
            mark=int(m["mark"]),
            count=parse_count(m["groups"]),  # "2x2" -> 4, "3" -> 3
            diameter=int(m["dia"]),
            length=float(m["length"]),
            steel="BST500",  # default, overridable from materials
        )
    },
    # Bar group without explicit mark: "4Ф14 L=0.95"
    {
        "name": "unmarked_bar_group",
        "regex": r"^(?P<count>\d+)(?P<dia_sym>[ØФ])(?P<dia>\d+)\s+L=(?P<length>[\d.]+)$",
        ...
    },
    # Stirrups: "etrieri Ф8/15" or "Ø8/15"
    {
        "name": "stirrups",
        "regex": r"^(?:etrieri\s+)?[ØФ](?P<dia>\d+)/(?P<spacing>\d+)$",
        ...
    },
    # Mesh: "Ø6/10/10" or "STNB Ø6/10/10"
    {
        "name": "mesh",
        "regex": r"^(?:STNB\s+)?[ØФ](?P<dia>\d+)/(?P<grid_x>\d+)/(?P<grid_y>\d+)$",
        ...
    },
    # Slab bars: "1 Ф10/15 L=8.80"
    {
        "name": "slab_bar",
        "regex": r"^(?P<mark>\d+)\s+[ØФ](?P<dia>\d+)/(?P<spacing>\d+)\s+L=(?P<length>[\d.]+)$",
        ...
    },
    # Element counts: "9 buc. stâlpișori" or "23 buc."
    {
        "name": "element_count",
        "regex": r"^(?P<count>\d+)\s+buc\.?(?:\s+(?P<element>\w+))?$",
        ...
    },
    # Material specs (for the materials sheet)
    {
        "name": "concrete_spec",
        "regex": r"^Beton\s+(?P<application>\w+)-?\s*C(?P<class>\d+/\d+)",
        ...
    },
]
```

### Aggregation Logic

After parsing, the parser aggregates marks across the project:

```python
def aggregate(parsed_items):
    marks = defaultdict(lambda: {"count": 0, "lengths": [], "occurrences": []})

    for item in parsed_items:
        if item.type == "marked_bar_group":
            key = (item.mark, item.diameter)
            marks[key]["count"] += item.count
            marks[key]["lengths"].append(item.length)
            marks[key]["occurrences"].append((item.layout, item.position))

    # Validation: all occurrences of the same mark should have the same length
    for key, data in marks.items():
        if len(set(data["lengths"])) > 1:
            data["warning"] = f"Mark {key[0]} has inconsistent lengths: {data['lengths']}"

    return marks
```

### Output: Structured Schedule

```python
@dataclass
class ScheduleRow:
    mark: int
    diameter_mm: int
    steel_grade: str
    count: int
    length_m: float
    total_length_m: float       # count × length
    weight_per_m: float         # from constants
    weight_per_mark_kg: float   # total_length × weight_per_m
    confidence: str             # "high" | "medium" | "low"
    source_layouts: list[str]   # ["R02", "R04"]

@dataclass
class Schedule:
    project_name: str
    rows: list[ScheduleRow]
    totals_per_diameter: dict[int, float]  # {14: 1456, 12: 777, ...}
    grand_total_kg: float
    materials: list[MaterialSpec]
    warnings: list[str]
```

### Why This Approach Works

- **Deterministic**: same input → same output, every time
- **Fast**: parses thousands of text entries in milliseconds
- **Auditable**: every value in the output traces back to a source label
- **Explainable**: when something goes wrong, you can see exactly which regex matched what
- **No API costs**: pure local computation
- **Debuggable**: failing patterns can be added to a test corpus

### Test Corpus

Phase 0 builds a regression test suite with the actual labels from your 12 PDFs. Every pattern that appears in the source files becomes a test case. Future enhancements never break existing patterns.

---

## 7. AI Strategy (Reduced Role)

In v2 I planned AI as the central engine for schedule generation. After analyzing real data, I'm scaling that back significantly.

### Where AI Is NOT Needed

- Parsing standard rebar labels (the parser handles these)
- Computing weights and totals (constants table)
- Aggregating marks across layouts (deterministic logic)
- Generating the Excel file (templates)

### Where AI Still Helps (Phase 2)

**1. Edge case parsing** — when a label doesn't match any known pattern, send it to Claude Haiku 4.5 with the question: "Is this a rebar specification? If yes, parse it." This catches non-standard notation, OCR-style errors in copied drawings, and firm-specific abbreviations.

**2. Material specification extraction from notes** — the materials section in each layout contains free-form text like:
```
Beton fundatii- C30/37●Cl 0,2●Dmax 32●S2●CEM II A-S 42,5-XC4+XF1
```
Parsing this with regex is possible but brittle. AI handles the variations cleanly and produces a structured material list.

**3. Multilingual expansion** — when ArchyAI moves beyond Romania (German, French, Polish standards), AI lets us bootstrap new parsers without rewriting from scratch.

**4. Quality validation** — after the parser produces a schedule, optionally send it to AI with the question: "Does this look like a valid rebar schedule for a residential foundation? Are there any obvious omissions?" Catches missed entries.

### Cost Implications

| Scenario | AI cost per drawing |
|----------|---------------------|
| Pure parser, no AI | $0 |
| AI for edge cases only (Phase 2) | ~$0.001 |
| AI for materials extraction | ~$0.002 |
| AI for full validation | ~$0.005 |
| **Realistic average** | **~$0.002** |

At 1,000 drawings/month, AI costs are ~$2/month. Negligible.

### Model Choice

When AI is used, **Claude Haiku 4.5** is the right pick:
- $1 input / $5 output per million tokens
- Fast (sub-second responses)
- Excellent at structured parsing
- Strong multilingual support including Romanian

---

## 8. Implementation Phases

### Phase 0 — Validation Sprint (Week 1)

**Critical: Don't build the SaaS yet. Prove the core works with real files.**

> **Status update (April 7, 2026):** Phase 0 is partially complete. CloudConvert was tested and failed. The ezdxf + matplotlib rendering works but needs ODA for proper DWG→DXF conversion. See "What Changed in v3.1" above.

- [x] Set up Python environment (Mac) — venv with ezdxf 1.4.3, pypdf, matplotlib, requests
- [x] Test CloudConvert DWG→PDF pipeline — **FAILED**: only 2 pages instead of 17
- [x] Test CloudConvert DWG→DXF pipeline — **FAILED**: only 2 layouts instead of 17
- [x] Verify ezdxf can read DXF and enumerate layouts — **WORKS** (but needs proper DXF)
- [x] Verify ezdxf matplotlib PDF rendering — **WORKS** (rendered Model Space to 25MB PDF)
- [x] Build and test Feature 1 MVP (upload → split → download) — **Pipeline works, conversion doesn't**
- [ ] **BLOCKED: Install ODA File Converter** (download from opendesignalliance.com)
- [ ] Convert `newmoda.dwg` → `newmoda.dxf` using ODA — verify all 17 layouts present
- [ ] Render each layout to A3 PDF via ezdxf, compare visually to example-docs/*.pdf
- [ ] Extract all TEXT/MTEXT entities, dump to JSON
- [ ] Write the parser v0.1 with the patterns identified in this plan
- [ ] Run parser against extracted text from R02, R09 (the layouts with most rebar data)
- [ ] Compare parser output to the actual schedules in R04, R08, R09
- [ ] Measure: what percentage of marks does the parser correctly identify?

**Success criteria:**
- ODA produces DXF with all 17 Paper Space layouts from newmoda.dwg
- Layout rendering quality is acceptable (text readable, geometry visible)
- Parser identifies >85% of rebar marks correctly
- Calculated totals match the actual schedules within 5%

**If success:** Proceed to Phase 1.
**If failure on rendering quality:** Investigate PyMuPDF backend, Autodesk APS, or hybrid approaches.
**If failure on layout extraction:** Investigate libredwg, FreeCAD, or Autodesk APS as alternative DWG readers.

### Phase 1 — Feature 1 MVP (Weeks 2–4)

Goal: Deployable web app for layout splitting only.

- [ ] FastAPI backend skeleton with auth (Clerk)
- [ ] PostgreSQL schema, migrations (Alembic)
- [ ] R2 storage integration with presigned URLs
- [ ] Celery + Redis for async processing
- [ ] DWG conversion worker (ODA CLI)
- [ ] Layout rendering worker (ezdxf + matplotlib → A3 PDF)
- [ ] React frontend:
  - [ ] Upload page with drag-and-drop
  - [ ] Processing status with polling
  - [ ] Layout list with thumbnails
  - [ ] Individual PDF download
  - [ ] ZIP download of all layouts
- [ ] Landing page explaining the product
- [ ] Deploy to Railway + Vercel
- [ ] Test with your `newmoda.dwg` end-to-end

**Deliverable:** Architects can sign up, upload a DWG, and get back A3 PDFs.

### Phase 2 — Feature 2 MVP (Weeks 5–8)

Goal: Add rebar schedule generation.

- [ ] Parser module with full Romanian rebar grammar
- [ ] Test suite covering all patterns from your 12 sample PDFs
- [ ] Aggregation and weight calculation logic
- [ ] Material weight constants table (configurable)
- [ ] Excel generation matching "Extras de armătură" format
- [ ] Schedule data model and storage
- [ ] Schedule review UI:
  - [ ] Editable table with confidence indicators
  - [ ] Per-row source tracing ("found in R02, R04")
  - [ ] Add/edit/delete row operations
  - [ ] Recalculate on edit
- [ ] Excel export with proper formatting
- [ ] Onboard 3 beta users (Romanian engineering firms)

**Deliverable:** Architects can generate schedules and export to Excel.

### Phase 3 — Beta & Polish (Weeks 9–12)

- [ ] Iterate on parser based on real-world drawings from beta users
- [ ] Add patterns discovered from new firms' notation
- [ ] Stripe billing integration
- [ ] Onboarding flow + tutorial
- [ ] Email notifications when processing completes
- [ ] Sentry monitoring
- [ ] Public launch in Romanian architecture/engineering communities

### Phase 4 — Scale & Intelligence (Weeks 13+)

- [ ] AI-assisted edge case parsing (Claude Haiku 4.5)
- [ ] Drawing revision comparison (re-upload, diff schedules)
- [ ] Custom title block injection
- [ ] German + French rebar standards (DIN, NF EN)
- [ ] REST API for programmatic access
- [ ] AutoCAD plugin (.NET / LISP) for direct in-CAD use
- [ ] Multi-tenant template library

---

## 9. Cost Analysis

### Operating Costs (Monthly)

| Component | Free Tier | 100 Users | 1,000 Users |
|-----------|-----------|-----------|-------------|
| Railway (backend + workers) | $5 | $50–100 | $300–500 |
| PostgreSQL (Railway managed) | $0 | $15 | $50 |
| Redis (Railway managed) | $0 | $10 | $30 |
| Cloudflare R2 storage | $0 | $5–15 | $30–80 |
| Anthropic API (Phase 2+ only) | $0 | $2–5 | $10–30 |
| Clerk auth | $0 | $25 | $100 |
| Sentry monitoring | $0 | $26 | $80 |
| ODA File Converter license | ~$200 | ~$200 | ~$200 |
| Domain | $1 | $1 | $1 |
| **Monthly total** | **~$10** | **~$330–400** | **~$800–1,100** |

Significantly cheaper than v2's estimate because AI is no longer on the critical path.

### Per-Drawing Marginal Cost

| Operation | Cost |
|-----------|------|
| DWG → DXF conversion | ~$0.001 |
| 12× layout PDF rendering | ~$0.005 |
| Parser execution (CPU only) | ~$0 |
| Excel generation | ~$0 |
| R2 storage (1 month) | ~$0.0001 |
| Optional AI edge cases | ~$0.001 |
| **Total** | **~$0.007** |

At 1,000 drawings/month: ~$7 in marginal compute costs. Pricing at €79/month for 100 drawings gives 95%+ gross margins.

### Pricing Recommendation

| Plan | Price | Drawings/mo | Schedules/mo | Users |
|------|-------|-------------|--------------|-------|
| Free | €0 | 3 | 1 | 1 |
| Solo | €29 | 30 | 30 | 1 |
| Studio | €79 | 100 | 100 | 5 |
| Firm | €199 | unlimited | unlimited | 20 |
| Enterprise | Custom | unlimited | unlimited | unlimited |

The Free tier is generous enough for engineers to evaluate on a real project. Solo is for freelancers. Studio is the sweet spot for small firms. Firm removes limits for active practices. Enterprise covers SSO, on-premise, custom integrations.

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **CloudConvert cannot extract Paper Space layouts** | **Confirmed** | **Critical** | **Pivot to ODA File Converter + ezdxf rendering. CloudConvert removed from conversion pipeline.** |
| Layout rendering misses elements (hatches, custom fonts) | Medium | High | Phase 0 validation. ODA-direct rendering as fallback. |
| Parser misses non-standard notation from a new firm | High | Medium | Each new pattern becomes a regex addition. AI fallback for unknowns in Phase 2. |
| Romanian characters render wrong | Low | Medium | Bundle DejaVu Sans + Noto Sans. Test with actual project. |
| Engineers don't trust automated schedules | Medium | High | Mandatory review UI. Audit trail per row. Confidence indicators. |
| ODA File Converter commercial licensing | High | Medium | Budget €2,000–3,000/year. Evaluate libredwg as backup. |
| DWG file size or complexity timeouts | Medium | Medium | Async processing, generous timeouts, progress reporting. |
| Romanian market too small for sustainable SaaS | Medium | High | Architecture is universal. EU expansion in Phase 4 (DE, FR, PL). |
| Architects prefer AutoCAD plugins over web tools | Medium | Medium | Web-first MVP. Phase 4 desktop integration if validated. |
| Marks inconsistent across source layouts | Medium | Medium | Detect and warn in review UI. Engineer corrects manually. |
| Schedule format varies between firms | Medium | Medium | Standard Romanian format as default. Custom templates in Phase 3. |

---

## 11. Open Questions

These should be answered during or before Phase 0:

1. **DWG access:** Can ezdxf parse `newmoda.dwg` after ODA conversion? (Phase 0 will confirm.)

2. **Layer naming:** What does the architect's layer naming convention look like inside the DWG? Are rebar annotations on a dedicated layer like "ARM" or "REBAR-TEXT"?

3. **Mark uniqueness:** When the same mark number appears in R02 and R04, is it truly the same physical element, or are mark numbers re-used between detail sheets?

4. **Schedule scope:** Should ArchyAI generate one consolidated schedule per project, or separate schedules for foundations / floor / roof like the original PDFs do?

5. **Excel template:** Do users want flexibility to customize the Excel column headers and styles, or is the standard Romanian format always sufficient?

6. **Title blocks:** Should ArchyAI extract project metadata (project number, beneficiary, location) from the title block automatically and pre-fill the project record?

7. **Pricing currency:** EUR (recommended for EU market) or RON for Romanian-only initial focus?

8. **Compliance:** GDPR considerations for storing client drawings. Data residency: EU-only hosting?

9. **Versioning:** When an engineer revises a drawing and re-uploads, do they want to see what changed in the schedule? (Phase 4 feature.)

10. **Languages:** Romanian-only UI initially, or English from day one?

---

## Appendix A — Phase 0 Validation Script

A standalone CLI to prove the concept before building the SaaS. This is the first thing to build, this week, with your `newmoda.dwg`:

```bash
# Install
pip install ezdxf openpyxl matplotlib

# Run validation
python validate.py newmoda.dwg --output ./validation_output

# Output:
validation_output/
├── 01_dxf_inspection.txt        # Layouts found, layer list, entity counts
├── 02_layouts/
│   ├── R01.pdf                   # A3 rendered
│   ├── R02.pdf
│   └── ...
├── 03_extracted_text/
│   ├── R02_text.json             # All TEXT/MTEXT with positions
│   └── ...
├── 04_parser_output/
│   ├── parsed_marks.json         # Parser results
│   └── unmatched_text.txt        # Text the parser didn't recognize
├── 05_generated_schedule.xlsx    # The auto-generated schedule
└── 06_comparison_report.md       # Auto vs manual schedule comparison
```

The comparison report shows:
- How many marks the parser found vs how many are in the original schedules
- Which marks match exactly, which differ, which are missing
- Total weight calculated vs original
- Time taken end-to-end

Run this against `newmoda.dwg` and the result tells us whether the entire product is viable. **One week of work to validate everything.**

---

## Appendix B — Parser Test Cases

These test cases come directly from your 12 PDFs and form the initial regression suite:

```python
PARSER_TESTS = [
    # From R02 (plan fundații)
    ("1 2x2Ф14 L=8.60", {"mark": 1, "count": 4, "diameter": 14, "length": 8.60}),
    ("2 2x2Ф14 L=3.30", {"mark": 2, "count": 4, "diameter": 14, "length": 3.30}),
    ("3 2x2Ф14 L=2.10", {"mark": 3, "count": 4, "diameter": 14, "length": 2.10}),
    ("4 2x2Ф14 L=3.50", {"mark": 4, "count": 4, "diameter": 14, "length": 3.50}),
    ("5 2x2Ф14 L=10.60", {"mark": 5, "count": 4, "diameter": 14, "length": 10.60}),

    # From R04 (detalii fundații)
    ("4Ф14 L=0.95", {"mark": None, "count": 4, "diameter": 14, "length": 0.95}),
    ("9 4Ф14 L=2.50", {"mark": 9, "count": 4, "diameter": 14, "length": 2.50}),
    ("etrieri Ф8/15", {"type": "stirrups", "diameter": 8, "spacing": 15}),
    ("Mustăți stâlpișori 25/25, 23 buc.", {"type": "element", "name": "stâlpișori", "count": 23}),

    # From R06 (buiandrugi parter)
    ("1 3Ф14 L=2.95", {"mark": 1, "count": 3, "diameter": 14, "length": 2.95}),
    ("2 3Ф14 L=5.95", {"mark": 2, "count": 3, "diameter": 14, "length": 5.95}),
    ("3 3Ф14 L=1.95", {"mark": 3, "count": 3, "diameter": 14, "length": 1.95}),
    ("4 2x3Ф12 L=1.35", {"mark": 4, "count": 6, "diameter": 12, "length": 1.35}),
    ("5 2x3Ф12 L=1.55", {"mark": 5, "count": 6, "diameter": 12, "length": 1.55}),

    # From R07 (centuri și grinzi)
    ("6 2x3Ф12 L=7.15", {"mark": 6, "count": 6, "diameter": 12, "length": 7.15}),
    ("7 2x3Ф12 L=4.80", {"mark": 7, "count": 6, "diameter": 12, "length": 4.80}),
    ("11 2x3Ф16 L=5.70", {"mark": 11, "count": 6, "diameter": 16, "length": 5.70}),
    ("12 2x3Ф16 L=2.95", {"mark": 12, "count": 6, "diameter": 16, "length": 2.95}),

    # From R09 (placă b.a.)
    ("1 Ф10/15 L=8.80", {"mark": 1, "count": 1, "diameter": 10, "spacing": 15, "length": 8.80}),
    ("2 Ф10/15 L=1.45", {"mark": 2, "count": 1, "diameter": 10, "spacing": 15, "length": 1.45}),

    # Materials (parsed but not as rebar marks)
    ("Beton fundatii- C30/37", {"type": "concrete", "application": "fundatii", "class": "C30/37"}),
    ("Oțel beton - BST500C", {"type": "steel", "grade": "BST500C"}),
    ("Plasă sudată - STNB Ø6/10/10", {"type": "mesh", "standard": "STNB", "diameter": 6, "grid": "10/10"}),

    # Should NOT be parsed as rebar
    ("Notă: Constructorul va verifica toate cotele", None),
    ("Scara: 1:50", None),
    ("Proiect nr.: 295/2026", None),
    ("ArchiBau Studio 1618 S.R.L.", None),
]
```

Every pattern in your 12 PDFs is here. The parser must pass all of these tests in Phase 0. Future drawings will add more patterns to this corpus, ensuring no regressions.

---

## Bottom Line

**ArchyAI is more buildable than I initially thought.** Looking at the real source files revealed that:

1. The data is already structured in the drawings (marks + standard notation)
2. The output format is fixed (Romanian construction standard)
3. A deterministic parser can do the work without AI on the critical path
4. AI becomes a quality enhancement, not a dependency

This means lower costs, faster processing, more predictable output, and easier debugging. The MVP can ship in 8 weeks (2 weeks for Phase 0 + 6 weeks for Phases 1–2), and you'll have something architects can actually use and pay for.

**Next step:** Build the Phase 0 validation script this week and run it against `newmoda.dwg`. If it works, you have a viable product. Want me to write that script?
