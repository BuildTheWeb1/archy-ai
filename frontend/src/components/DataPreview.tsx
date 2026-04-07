import type { ExtractionResult, MappingItem } from "../types";

interface Props {
  extraction: ExtractionResult;
  mappings: MappingItem[];
  onExport: () => void;
  isExporting: boolean;
}

function getFieldValue(entity: Record<string, unknown>, field: string): string {
  if (field === "text") return String(entity.text ?? "");
  if (field === "measurement") return String(entity.measurement ?? "");
  if (field === "block_name") return String(entity.block_name ?? "");
  if (field === "radius") return String(entity.radius ?? "");
  if (field === "area") {
    const pts = entity.points as number[][] | undefined;
    if (entity.is_closed && pts && pts.length >= 3) return "~area";
    return "";
  }
  if (field.startsWith("attr:")) {
    const tag = field.split(":", 1)[1] || field.slice(5);
    const attrs = entity.attributes as Record<string, string> | undefined;
    return attrs?.[tag] ?? "";
  }
  return "";
}

export function DataPreview({ extraction, mappings, onExport, isExporting }: Props) {
  if (mappings.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
        <p className="text-slate-400 text-sm">Add at least one column mapping to see a preview.</p>
      </div>
    );
  }

  // Build preview rows: for each mapping, pull entities; zip up to 20 rows
  const perMapping = mappings.map((m) => {
    const layer = extraction.layers[m.layer];
    if (!layer) return [];
    return layer.entities
      .filter((e) => e.type === m.entity_type)
      .slice(0, 20)
      .map((e) => getFieldValue(e as unknown as Record<string, unknown>, m.field));
  });

  const maxRows = Math.max(...perMapping.map((r) => r.length), 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">
            Preview <span className="text-slate-400 font-normal">(first 20 rows per column)</span>
          </h2>
        </div>
        <button
          onClick={onExport}
          disabled={isExporting || mappings.length === 0}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors"
        >
          {isExporting ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          )}
          Export .xlsx
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm border-collapse min-w-max">
          <thead>
            <tr className="bg-blue-700 text-white text-xs">
              <th className="px-3 py-2 text-left font-medium text-blue-200 w-10 border-r border-blue-600">#</th>
              {mappings.map((m, i) => (
                <th key={i} className="px-3 py-2 text-left font-semibold border-r border-blue-600 last:border-r-0">
                  <div className="truncate max-w-[140px]">{m.column_name}</div>
                  <div className="font-normal text-blue-300 truncate max-w-[140px]">
                    {m.layer} / {m.entity_type}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: maxRows }, (_, rowIdx) => (
              <tr
                key={rowIdx}
                className={rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50"}
              >
                <td className="px-3 py-2 text-slate-400 text-xs border-r border-slate-100">{rowIdx + 1}</td>
                {perMapping.map((col, colIdx) => (
                  <td key={colIdx} className="px-3 py-2 text-slate-700 border-r border-slate-100 last:border-r-0">
                    <span className="truncate block max-w-[180px]">{col[rowIdx] ?? ""}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {maxRows === 0 && (
        <p className="text-center text-slate-400 text-sm mt-4">
          No entities matched the current mappings.
        </p>
      )}
    </div>
  );
}
