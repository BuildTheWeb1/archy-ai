import type { MappingItem } from "../types";

interface Props {
  mappings: MappingItem[];
  onRemove: (index: number) => void;
  onReorder: (from: number, to: number) => void;
}

export function MappingBuilder({ mappings, onRemove, onReorder }: Props) {
  return (
    <div className="flex flex-col h-full">
      <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Output Columns
      </h2>

      {mappings.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-4 border-2 border-dashed border-slate-200 rounded-xl">
          <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center mb-3">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 0v10m0-10a2 2 0 012 2h2a2 2 0 012-2v0" />
            </svg>
          </div>
          <p className="text-slate-500 text-sm font-medium">No columns yet</p>
          <p className="text-slate-400 text-xs mt-1">
            Click a layer entity type on the left to add a column
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {mappings.map((m, i) => (
            <div
              key={i}
              className="bg-white border border-slate-200 rounded-xl px-3 py-2.5 flex items-center gap-3"
            >
              {/* Drag handle */}
              <div className="flex flex-col gap-0.5 cursor-grab shrink-0">
                {[0, 1, 2].map((r) => (
                  <div key={r} className="flex gap-0.5">
                    <div className="w-1 h-1 rounded-full bg-slate-300" />
                    <div className="w-1 h-1 rounded-full bg-slate-300" />
                  </div>
                ))}
              </div>

              {/* Column number badge */}
              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center shrink-0">
                {i + 1}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">{m.column_name}</p>
                <p className="text-xs text-slate-400 truncate">
                  {m.layer} · {m.entity_type} · {m.field}
                </p>
              </div>

              {/* Reorder */}
              <div className="flex flex-col gap-0.5">
                <button
                  onClick={() => onReorder(i, i - 1)}
                  disabled={i === 0}
                  className="p-0.5 rounded hover:bg-slate-100 disabled:opacity-30 transition-colors"
                >
                  <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                <button
                  onClick={() => onReorder(i, i + 1)}
                  disabled={i === mappings.length - 1}
                  className="p-0.5 rounded hover:bg-slate-100 disabled:opacity-30 transition-colors"
                >
                  <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>

              {/* Remove */}
              <button
                onClick={() => onRemove(i)}
                className="p-1 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors shrink-0"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
