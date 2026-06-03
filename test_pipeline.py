"""
Quick test: run the pipeline on PDFs 2, 3, 4 and compare against expected output.
Run from the backend directory:
    cd backend && source venv/bin/activate && python ../test_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from pipeline.orchestrator import run_pipeline

# Expected values from the screenshot
EXPECTED = [
    {"mark": 1,  "diameter": 14, "count": 40,  "length": 8.60},
    {"mark": 2,  "diameter": 14, "count": 8,   "length": 3.30},
    {"mark": 3,  "diameter": 14, "count": 16,  "length": 2.10},
    {"mark": 4,  "diameter": 14, "count": 24,  "length": 3.50},
    {"mark": 5,  "diameter": 14, "count": 24,  "length": 10.60},
    {"mark": 6,  "diameter": 8,  "count": 620, "length": 1.25},
    {"mark": 7,  "diameter": 8,  "count": 310, "length": 1.35},
    {"mark": 8,  "diameter": 10, "count": 16,  "length": 2.10},
    {"mark": 9,  "diameter": 14, "count": 92,  "length": 2.50},
    {"mark": 10, "diameter": 8,  "count": 207, "length": 0.95},
    {"mark": 11, "diameter": 14, "count": 136, "length": 1.70},
]

pdf_paths = [
    Path(__file__).parent / "example-docs" / "2.pdf",
    Path(__file__).parent / "example-docs" / "3.pdf",
    Path(__file__).parent / "example-docs" / "4.pdf",
]

print("Running pipeline on PDFs 2, 3, 4...\n")
rows, warnings = run_pipeline(pdf_paths)

# Index results by mark number
result_by_mark = {r["mark"]: r for r in rows if r["mark"] is not None}

# Print comparison table
W = 80
print("=" * W)
print(f"{'COMPARISON: GOT vs EXPECTED':^{W}}")
print("=" * W)
print(f"{'Marca':>6} {'Ø exp':>6} {'Ø got':>6} {'Buc exp':>8} {'Buc got':>8} {'L exp':>7} {'L got':>7} {'Match?':>8}")
print("-" * W)

all_ok = True
for exp in EXPECTED:
    m = exp["mark"]
    got = result_by_mark.get(m)
    if got is None:
        print(f"{m:>6} {exp['diameter']:>6} {'???':>6} {exp['count']:>8} {'???':>8} {exp['length']:>7.2f} {'???':>7} {'❌ MISSING':>8}")
        all_ok = False
        continue

    diam_ok = got["diameter"] == exp["diameter"]
    count_ok = got["count"] == exp["count"]
    len_ok = abs(got["length"] - exp["length"]) < 0.01
    ok = diam_ok and count_ok and len_ok
    if not ok:
        all_ok = False

    status = "✅ OK" if ok else "❌ WRONG"
    print(
        f"{m:>6} {exp['diameter']:>6} {got['diameter']:>6} "
        f"{exp['count']:>8} {got['count']:>8} "
        f"{exp['length']:>7.2f} {got['length']:>7.2f} {status:>8}"
    )

# Unexpected marks
extra = [r for r in rows if r["mark"] not in {e["mark"] for e in EXPECTED}]
if extra:
    print(f"\nUnexpected marks in output:")
    for r in extra:
        print(f"  Mark {r['mark']}: Ø{r['diameter']}, {r['count']} buc, L={r['length']}")

print("=" * W)
print(f"\nResult: {'✅ ALL CORRECT' if all_ok else '❌ MISMATCHES FOUND'}")
print(f"Rows returned: {len(rows)}, Expected: {len(EXPECTED)}")

if warnings:
    print(f"\nWarnings ({len(warnings)}):")
    for w in warnings:
        print(f"  · {w}")
