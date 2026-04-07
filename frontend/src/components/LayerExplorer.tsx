import { useState } from "react";
import type { LayerSummary, MappingItem } from "../types";
import { FIELD_OPTIONS_BY_TYPE } from "../types";

interface Props {
  layers: LayerSummary;
  mappings: MappingItem[];
  onAddMapping: (mapping: MappingItem) => void;
}

export function LayerExplorer({ layers, mappings, onAddMapping }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ layer: string; type: string } | null>(null);
  const [columnName, setColumnName] = useState("");
  const [field, setField] = useState("");

  const sortedLayers = Object.entries(layers).sort((a, b) =>
    b[1].entity_count - a[1].entity_count
  );

  const handleSelect = (layer: string, type: string) => {
    setSelected({ layer, type });
    setColumnName(`${layer} — ${type}`);
    const options = FIELD_OPTIONS_BY_TYPE[type] ?? [];
    setField(options[0]?.value ?? "text");
  };

  const handleAdd = () => {
    if (!selected || !columnName.trim() || !field) return;
    onAddMapping({
      layer: selected.layer,
      entity_type: selected.type,
      field,
      column_name: columnName.trim(),
    });
    setSelected(null);
    setColumnName("");
    setField("");
  };

  const isAlreadyMapped = (layer: string, type: string) =>
    mappings.some((m) => m.layer === layer && m.entity_type === type);

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Layers &amp; Entities
      </h2>

      {/* Layer list */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1">
        {sortedLayers.map(([name, info]) => (
          <div key={name} className="rounded-lg border border-slate-200 overflow-hidden">
            {/* Layer header */}
            <button
              className="w-full flex items-center justify-between px-3 py-2.5 bg-white hover:bg-slate-50 text-left transition-colors"
              onClick={() => setExpanded(expanded === name ? null : name)}
            >
              <span className="font-medium text-slate-800 text-sm truncate">{name}</span>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                <span className="text-xs text-slate-400">{info.entity_count} entities</span>
                <svg
                  className={`w-4 h-4 text-slate-400 transition-transform ${expanded === name ? "rotate-90" : ""}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>

            {/* Entity types */}
            {expanded === name && (
              <div className="border-t border-slate-100 bg-slate-50 px-2 py-1.5 space-y-1">
                {info.entity_types.map((type) => {
                  const mapped = isAlreadyMapped(name, type);
                  const active = selected?.layer === name && selected?.type === type;
                  return (
                    <button
                      key={type}
                      onClick={() => handleSelect(name, type)}
                      disabled={mapped}
                      className={[
                        "w-full flex items-center justify-between px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                        mapped
                          ? "bg-green-50 text-green-700 cursor-default"
                          : active
                          ? "bg-blue-100 text-blue-800 ring-1 ring-blue-300"
                          : "bg-white text-slate-700 hover:bg-blue-50 hover:text-blue-700 cursor-pointer",
                      ].join(" ")}
                    >
                      <span>{type}</span>
                      {mapped && (
                        <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Mapping form — appears when a type is selected */}
      {selected && (
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
          <p className="text-xs font-semibold text-blue-800">
            Map <span className="font-bold">{selected.type}</span> from <span className="font-bold">{selected.layer}</span>
          </p>

          <div>
            <label className="text-xs text-slate-600 block mb-1">Field to extract</label>
            <select
              value={field}
              onChange={(e) => setField(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              {(FIELD_OPTIONS_BY_TYPE[selected.type] ?? [{ value: "text", label: "Text content" }]).map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-600 block mb-1">Column name</label>
            <input
              type="text"
              value={columnName}
              onChange={(e) => setColumnName(e.target.value)}
              placeholder="e.g. Beam ID"
              className="w-full text-sm border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!columnName.trim()}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg py-1.5 transition-colors"
            >
              Add column
            </button>
            <button
              onClick={() => setSelected(null)}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
