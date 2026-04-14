import { useCallback, useState } from "react";
import type { Confidence, ScheduleRow } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface Props {
  rows: ScheduleRow[];
  onChange: (rows: ScheduleRow[]) => void;
}

function fmt(n: number) {
  return n.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
}

function recalcRow(row: ScheduleRow): ScheduleRow {
  const total_length = Math.round(row.count * row.length * 1000) / 1000;
  const weight = Math.round(total_length * row.weight_per_meter * 1000) / 1000;
  return { ...row, total_length, weight };
}

const DIAMETERS = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32];
const WEIGHTS: Record<number, number> = {
  6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888,
  14: 1.21, 16: 1.58, 18: 2.0, 20: 2.47,
  22: 2.984, 25: 3.853, 28: 4.83, 32: 6.31,
};

function newRow(): ScheduleRow {
  return {
    id: crypto.randomUUID(),
    mark: null,
    diameter: 10,
    steel_type: "BST500",
    count: 1,
    length: 1.0,
    total_length: 1.0,
    weight_per_meter: WEIGHTS[10],
    weight: WEIGHTS[10],
    confidence: "low",
    warnings: ["Adăugat manual"],
  };
}

export function ScheduleTable({ rows, onChange }: Props) {
  const [editingCell, setEditingCell] = useState<{ rowId: string; field: string } | null>(null);

  const updateRow = useCallback(
    (id: string, patch: Partial<ScheduleRow>) => {
      const updated = rows.map((r) => {
        if (r.id !== id) return r;
        let next = { ...r, ...patch };
        if (patch.diameter !== undefined) {
          next.weight_per_meter = WEIGHTS[patch.diameter] ?? r.weight_per_meter;
        }
        return recalcRow(next);
      });
      onChange(updated);
    },
    [rows, onChange],
  );

  const deleteRow = useCallback(
    (id: string) => onChange(rows.filter((r) => r.id !== id)),
    [rows, onChange],
  );

  const addRow = useCallback(() => onChange([...rows, newRow()]), [rows, onChange]);

  // Totals
  const grandTotal = rows.reduce((s, r) => s + r.weight, 0);

  const EditableNum = ({
    rowId,
    field,
    value,
    min,
    step,
  }: {
    rowId: string;
    field: string;
    value: number;
    min?: number;
    step?: number;
  }) => {
    const active = editingCell?.rowId === rowId && editingCell?.field === field;
    return active ? (
      <input
        autoFocus
        type="number"
        min={min ?? 0}
        step={step ?? 1}
        defaultValue={value}
        className="w-full text-right bg-blue-50 border border-blue-300 rounded px-1 text-sm"
        onBlur={(e) => {
          const n = parseFloat(e.target.value);
          if (!isNaN(n)) updateRow(rowId, { [field]: n } as Partial<ScheduleRow>);
          setEditingCell(null);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === "Escape") (e.target as HTMLInputElement).blur();
        }}
      />
    ) : (
      <span
        className="cursor-pointer hover:bg-blue-50 rounded px-1 select-none block text-right"
        onClick={() => setEditingCell({ rowId, field })}
      >
        {fmt(value)}
      </span>
    );
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-800 text-white">
            {[
              "Marca", "Ø [mm]", "Oțel", "Buc.", "Lung. [m]",
              "Lung./Ø [m]", "Masa Ø/m [kg/m]", "Masa/Ø [kg]", "Conf.", "",
            ].map((h) => (
              <th key={h} className="px-3 py-2 text-center font-semibold whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={10} className="text-center text-slate-400 py-8">
                Nicio înregistrare. Adăugați manual sau rulați extracția.
              </td>
            </tr>
          )}

          {rows.map((row, idx) => (
            <tr
              key={row.id}
              className={`border-b border-slate-100 ${idx % 2 === 0 ? "bg-white" : "bg-slate-50"} hover:bg-blue-50/40`}
            >
              {/* Marca */}
              <td className="px-3 py-1.5 text-center">
                {editingCell?.rowId === row.id && editingCell.field === "mark" ? (
                  <input
                    autoFocus
                    type="number"
                    min={1}
                    defaultValue={row.mark ?? ""}
                    className="w-16 text-center bg-blue-50 border border-blue-300 rounded px-1 text-sm"
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      updateRow(row.id, { mark: v === "" ? null : parseInt(v) });
                      setEditingCell(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === "Escape") (e.target as HTMLInputElement).blur();
                    }}
                  />
                ) : (
                  <span
                    className="cursor-pointer hover:bg-blue-50 rounded px-2 py-0.5 inline-block min-w-[2rem] text-center"
                    onClick={() => setEditingCell({ rowId: row.id, field: "mark" })}
                  >
                    {row.mark ?? "—"}
                  </span>
                )}
              </td>

              {/* Diameter */}
              <td className="px-3 py-1.5 text-center">
                <select
                  value={row.diameter}
                  onChange={(e) => updateRow(row.id, { diameter: parseInt(e.target.value) })}
                  className="bg-transparent border-0 text-center cursor-pointer hover:bg-blue-50 rounded text-sm w-full"
                >
                  {DIAMETERS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </td>

              {/* Steel type */}
              <td className="px-3 py-1.5 text-center text-slate-600">{row.steel_type}</td>

              {/* Count */}
              <td className="px-3 py-1.5">
                <EditableNum rowId={row.id} field="count" value={row.count} min={1} />
              </td>

              {/* Length */}
              <td className="px-3 py-1.5">
                <EditableNum rowId={row.id} field="length" value={row.length} min={0.01} step={0.01} />
              </td>

              {/* Total length (computed) */}
              <td className="px-3 py-1.5 text-right text-slate-500">{fmt(row.total_length)}</td>

              {/* Weight/m (computed) */}
              <td className="px-3 py-1.5 text-right text-slate-500">{row.weight_per_meter.toFixed(3)}</td>

              {/* Weight (computed) */}
              <td className="px-3 py-1.5 text-right font-medium">{fmt(row.weight)}</td>

              {/* Confidence */}
              <td className="px-3 py-1.5 text-center">
                <ConfidenceBadge confidence={row.confidence as Confidence} />
              </td>

              {/* Delete */}
              <td className="px-2 py-1.5 text-center">
                <button
                  onClick={() => deleteRow(row.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors"
                  title="Șterge rând"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>

        {rows.length > 0 && (
          <tfoot>
            <tr className="bg-slate-100 font-semibold border-t-2 border-slate-300">
              <td colSpan={7} className="px-3 py-2 text-right">TOTAL</td>
              <td className="px-3 py-2 text-right">{fmt(grandTotal)} kg</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        )}
      </table>

      <div className="mt-3 px-1">
        <button
          onClick={addRow}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
        >
          <span className="text-lg leading-none">+</span> Adaugă rând
        </button>
      </div>
    </div>
  );
}
