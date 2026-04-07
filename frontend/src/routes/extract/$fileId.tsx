import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useLayers, useExtraction } from "../../hooks/useExtraction";
import { LayerExplorer } from "../../components/LayerExplorer";
import { MappingBuilder } from "../../components/MappingBuilder";
import type { MappingItem } from "../../types";

export const Route = createFileRoute("/extract/$fileId")({
  component: ExtractPage,
});

function ExtractPage() {
  const { fileId } = Route.useParams();
  const navigate = useNavigate();
  const [mappings, setMappings] = useState<MappingItem[]>([]);

  const { data: layers, isLoading, isError } = useLayers(fileId);
  const { data: extraction } = useExtraction(fileId);

  const handleAdd = (m: MappingItem) =>
    setMappings((prev) => [...prev, m]);

  const handleRemove = (i: number) =>
    setMappings((prev) => prev.filter((_, idx) => idx !== i));

  const handleReorder = (from: number, to: number) => {
    if (to < 0 || to >= mappings.length) return;
    setMappings((prev) => {
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  };

  const handlePreview = () => {
    // Store mappings in sessionStorage so the preview page can access them
    sessionStorage.setItem(`mappings-${fileId}`, JSON.stringify(mappings));
    navigate({ to: "/preview/$fileId", params: { fileId } });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isError || !layers) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-600">
        Failed to load extraction. <Link to="/" className="ml-2 underline">Try again</Link>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Page header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="font-semibold text-slate-900">
            {extraction?.original_filename ?? extraction?.filename ?? "Drawing"}
          </h1>
          <p className="text-xs text-slate-400">
            {extraction ? `${extraction.layer_count} layers · ${extraction.total_entities} entities · ${extraction.dxf_version}` : "Loading…"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/" className="text-sm text-slate-500 hover:text-slate-700">
            ← New file
          </Link>
          <button
            onClick={handlePreview}
            disabled={mappings.length === 0}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors"
          >
            Preview &amp; Export
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Two-pane layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Layer Explorer */}
        <div className="w-80 border-r border-slate-200 bg-white p-4 flex flex-col overflow-hidden">
          <LayerExplorer
            layers={layers}
            mappings={mappings}
            onAddMapping={handleAdd}
          />
        </div>

        {/* Right: Mapping Builder */}
        <div className="flex-1 bg-slate-50 p-4 flex flex-col overflow-hidden">
          <MappingBuilder
            mappings={mappings}
            onRemove={handleRemove}
            onReorder={handleReorder}
          />

          {mappings.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <button
                onClick={handlePreview}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition-colors"
              >
                Preview &amp; Export →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
