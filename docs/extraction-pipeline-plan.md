# Rebar Extraction Pipeline — Implementation Plan

## Problem Statement

Structural engineers upload 1–4 PDF pages (planșe de armare) from a construction project. The system must analyse the drawings and produce an "Extras de armătură" table with: mark number, diameter, steel type, piece count (Buc.), bar length, total length per diameter, and total weight.

The calculations range from simple multiplication to geometric reasoning that cross-references multiple PDFs.

## Key Insight: Separate Reading from Calculating

A single "look at everything and give me the table" prompt fails because the AI conflates reading annotations with performing arithmetic and geometric calculations. Instead, the AI should **only read** (extract raw data from images) and **code should calculate** (do the math).

---

## Difficulty Tiers for Count Calculation

### Tier 1 — Explicit Count (Easy)
The drawing title states the element count directly.
- Example: "Mustăți stâlpișori 25/25, **23 buc.**" with mark ⑨ = 4Ø14 L=2.50
- Calculation: 4 bars × 23 elements = 92 Buc.
- AI task: Read the title count + mark annotation

### Tier 2 — Count from Plan (Medium)
The circled mark number appears multiple times on the plan view. Each occurrence represents one placement of that bar group.
- Example: Mark ① (2x2Ø14 L=8.60) appears 10 times on the foundation plan
- Calculation: 4 bars × 10 occurrences = 40 Buc.
- AI task: Count how many times each circled mark number appears on the plan

### Tier 3 — Geometric Calculation (Hard)
Stirrup counts require measuring total foundation beam lengths from the plan dimensions and dividing by the stirrup spacing defined in a cross-section on a different PDF.
- Example: Mark ⑥ (Ø8/15, L=1.25) — stirrups at 15cm spacing across foundation beams
- Calculation: Total beam length (from PDF 2 dimensions) ÷ 0.15m = 620 Buc.
- AI task: Read all beam segment dimensions from the plan + read stirrup spacing from sections
- Code task: Sum beam lengths, divide by spacing

---

## Multi-Step Pipeline

### Step 1 — Page Classification
**One quick AI call per PDF page.**

Prompt: "Is this page a plan view, cross-section detail, 3D construction detail, or non-structural (e.g., excavation plan)? What structural elements does it show?"

Output: `{ "type": "plan" | "cross_section" | "detail" | "non_structural", "description": "..." }`

Purpose: Skip irrelevant pages (like excavation plans), route each page to the correct extraction prompt.

### Step 2 — Raw Data Extraction (per page type)

#### For Plan Views (e.g., PDF 2 — "Plan fundații")
Prompt focus: **List circled marks + count occurrences + read beam dimensions**

Expected output:
```json
{
  "marks": [
    {
      "mark": 1,
      "annotation": "2x2Ø14 L=8.60",
      "diameter": 14,
      "bars_per_occurrence": 4,
      "length": 8.60,
      "occurrences_on_plan": 10,
      "occurrence_locations": ["row D'", "row D", "row C", "row B", "row A", ...]
    }
  ],
  "beam_segments": [
    { "from": "D'1", "to": "D'4", "length_cm": 891, "type": "horizontal" },
    { "from": "A1", "to": "A2", "length_cm": 243.8, "type": "horizontal" }
  ],
  "columns": [
    { "name": "SD1", "section": "25/25", "position": "D-1" },
    { "name": "S3", "section": "25/25", "position": "D-2" }
  ]
}
```

#### For Cross-Section Details (e.g., PDF 3 — "Detalii fundații I")
Prompt focus: **List every rebar/stirrup specification with its context**

Expected output:
```json
{
  "sections": [
    {
      "name": "Secțiune fundație pereți ext.",
      "foundation_type": "exterior_wall",
      "stirrups": [
        { "diameter": 8, "spacing_cm": 15, "length": 1.25, "mark": 6 },
        { "diameter": 8, "spacing_cm": 30, "length": 1.35, "mark": 7 }
      ],
      "longitudinal_bars": [
        { "annotation": "2x2Ø14", "diameter": 14, "bars": 4, "description": "Armare centură" }
      ]
    },
    {
      "name": "Secțiune fundație scară interioară",
      "foundation_type": "staircase",
      "special_bars": [
        { "annotation": "2Ø10/15 L=2.10", "diameter": 10, "count_per_set": 2, "length": 2.10, "mark": 8, "description": "Mustăți scară" }
      ]
    }
  ]
}
```

#### For Construction Details (e.g., PDF 4 — "Detalii fundații II")
Prompt focus: **Element counts + per-element bar specs + anchor details**

Expected output:
```json
{
  "elements": [
    {
      "name": "Mustăți stâlpișori",
      "section": "25/25",
      "count": 23,
      "marks": [
        { "mark": 9, "annotation": "4Ø14 L=2.50", "diameter": 14, "bars_per_element": 4, "length": 2.50 },
        { "mark": 10, "annotation": "etrieri Ø8/15 L=0.95, 9 buc.", "diameter": 8, "stirrups_per_element": 9, "length": 0.95 }
      ]
    },
    {
      "name": "Detaliu ancorare bare",
      "marks": [
        { "mark": 11, "annotation": "2x3Ø14 L=1.70", "diameter": 14, "bars_per_junction": 6, "length": 1.70 }
      ]
    }
  ]
}
```

### Step 3 — Schedule Calculation (Code, not AI)

The orchestrator combines extracted data:

```
For each mark:
  if element_count is explicit (e.g., "23 buc."):
    Buc = bars_per_element × element_count
  elif mark counted from plan:
    Buc = bars_per_occurrence × occurrences_on_plan
  elif stirrup with spacing:
    total_beam_length = sum(relevant beam segments from plan)
    Buc = ceil(total_beam_length / spacing)

  total_length = Buc × length_per_bar
  weight = total_length × weight_per_meter[diameter]
```

### Step 4 — Engineer Review

Present the extracted schedule in an editable table with:
- Confidence level per row (high/medium/low)
- Tier 1 marks → high confidence
- Tier 2 marks → medium confidence (counting may be off)
- Tier 3 marks (stirrups) → low confidence (geometric calc may be wrong)
- Warnings for any uncertain values
- Engineer corrects, then exports to Excel

---

## Model Selection Strategy

**MVP: Use Claude Sonnet (claude-sonnet-4-20250514)**
- Engineering drawings have rotated text, small fonts, overlapping annotations, mixed Cyrillic Ф / Latin Ø
- Counting circled marks on a busy plan requires careful visual scanning
- Sonnet is more reliable for accuracy on dense visual content

**Future optimisation: Test Haiku for cost reduction**
- Step 1 (page classification) could use Haiku — it's a simple categorisation task
- Steps 2a/2b/2c (data extraction) — test Haiku vs Sonnet on the same PDFs
- If Haiku gets ≥90% of values correct, switch (engineer reviews anyway)
- Hybrid approach: Haiku for easy steps, Sonnet for hard extraction

**Cost comparison (approximate, per project with 4 PDFs):**
- Sonnet: ~4 API calls × large image payloads → ~$0.10–0.30 per project
- Haiku: ~4 API calls → ~$0.01–0.05 per project
- Hybrid: ~$0.05–0.15 per project

---

## Example: Tracing All 11 Marks

Based on analysis of the example project (Proiect 295/2026):

### PDF 1 (R01 — Plan săpătură)
Non-structural. No rebar. Skip.

### PDF 2 (R02 — Plan fundații) → Marks 1–5
All marks use "2x2Ø14" = 4 bars of Ø14mm per foundation strip.

| Mark | Annotation | L [m] | Source | Count logic | Buc. |
|------|-----------|-------|--------|-------------|------|
| 1 | 2x2Ø14 L=8.60 | 8.60 | Horizontal centuri (plan count) | 4 × 10 strips | 40 |
| 2 | 2x2Ø14 L=3.30 | 3.30 | Short horizontal strip (plan count) | 4 × 2 strips | 8 |
| 3 | 2x2Ø14 L=2.10 | 2.10 | Perpendicular stubs (plan count) | 4 × 4 locations | 16 |
| 4 | 2x2Ø14 L=3.50 | 3.50 | Vertical strips A–B (plan count) | 4 × 6 locations | 24 |
| 5 | 2x2Ø14 L=10.60 | 10.60 | Long vertical centuri (plan count) | 4 × 6 locations | 24 |

### PDF 3 (R03 — Detalii fundații I) → Marks 6–8
Cross-section details define stirrup types and special bars.

| Mark | Annotation | L [m] | Source | Count logic | Buc. |
|------|-----------|-------|--------|-------------|------|
| 6 | Ø8/15 L=1.25 | 1.25 | Stirrups in foundation beams | total_beam_length ÷ 0.15 | 620 |
| 7 | Ø8/30 L=1.35 | 1.35 | Stirrups in foundation beams | total_beam_length ÷ 0.30 | 310 |
| 8 | 2Ø10/15 L=2.10 | 2.10 | Staircase whiskers (mustăți scară) | specific to stair geometry | 16 |

### PDF 4 (R04 — Detalii fundații II) → Marks 9–11

| Mark | Annotation | L [m] | Source | Count logic | Buc. |
|------|-----------|-------|--------|-------------|------|
| 9 | 4Ø14 L=2.50 | 2.50 | Mustăți stâlpișori (23 buc.) | 4 × 23 | 92 |
| 10 | etrieri Ø8/15, 9 buc, L=0.95 | 0.95 | Stirrups in stâlpișori (23 buc.) | 9 × 23 | 207 |
| 11 | 2x3Ø14 L=1.70 | 1.70 | Anchor bars at junctions | 6 × junction_count | 136 |

### Expected Final Table

| Marca | Ø [mm] | Oțel | Buc. | Lung. [m] | Lung./Ø 8 | Lung./Ø 10 | Lung./Ø 14 |
|-------|--------|------|------|-----------|-----------|------------|------------|
| 1 | 14 | BST500 | 40 | 8.60 | | | 344.0 |
| 2 | 14 | BST500 | 8 | 3.30 | | | 26.4 |
| 3 | 14 | BST500 | 16 | 2.10 | | | 33.6 |
| 4 | 14 | BST500 | 24 | 3.50 | | | 84.0 |
| 5 | 14 | BST500 | 24 | 10.60 | | | 254.4 |
| 6 | 8 | BST500 | 620 | 1.25 | 775.0 | | |
| 7 | 8 | BST500 | 310 | 1.35 | 418.5 | | |
| 8 | 10 | BST500 | 16 | 2.10 | | 33.6 | |
| 9 | 14 | BST500 | 92 | 2.50 | | | 230.0 |
| 10 | 8 | BST500 | 207 | 0.95 | 196.7 | | |
| 11 | 14 | BST500 | 136 | 1.70 | | | 231.2 |
| **Masa totală** | | | | | **549 kg** | **21 kg** | **1456 kg** |
| **TOTAL** | | | | | | | **2026 kg** |

---

## Weight Constants (kg/m by diameter)

| Ø [mm] | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 22 | 25 | 28 | 32 |
|--------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| kg/m | 0.222 | 0.395 | 0.617 | 0.888 | 1.210 | 1.580 | 2.000 | 2.470 | 2.984 | 3.853 | 4.830 | 6.310 |

---

## Implementation Phases

### Phase 1 (MVP)
- Multi-step pipeline with Sonnet
- Page classification → per-type extraction → code calculation → review
- Confidence tiers: high (tier 1), medium (tier 2), low (tier 3)
- Engineer reviews and corrects before export

### Phase 2
- Test Haiku for cost reduction on classification and simpler extraction
- Improve stirrup counting accuracy with better geometric prompts
- Learn from engineer corrections to refine prompts

### Phase 3
- Pattern recognition across projects (similar buildings = similar schedules)
- Template-based extraction for common structural types
- Batch processing for larger projects
