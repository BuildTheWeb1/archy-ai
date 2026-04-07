import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useExtraction, useExport } from "../../hooks/useExtraction";
import { DataPreview } from "../../components/DataPreview";
import type { MappingItem } from "../../types";

export const Route = createFileRoute("/preview/$fileId")({
  component: PreviewPage,
});

function PreviewPage() {
  const { fileId } = Route.useParams();

  // Restore mappings saved by the extract page
  const [mappings] = useState<MappingItem[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem(`mappings-${fileId}`) ?? "[]");
    } catch {
      return [];
    }
  });

  const { data: extraction, isLoading, isError } = useExtraction(fileId);
  const exportMutation = useExport(fileId);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isError || !extraction) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-600">
        Failed to load data. <Link to="/" className="ml-2 underline">Start over</Link>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Page header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="font-semibold text-slate-900">
            {extraction.original_filename ?? extraction.filename}
          </h1>
          <p className="text-xs text-slate-400">
            {mappings.length} column{mappings.length !== 1 ? "s" : ""} mapped
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/extract/$fileId"
            params={{ fileId }}
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            ← Edit mappings
          </Link>
          <Link to="/" className="text-sm text-slate-500 hover:text-slate-700">
            New file
          </Link>
        </div>
      </div>

      {/* Export success banner */}
      {exportMutation.isSuccess && (
        <div className="bg-green-50 border-b border-green-200 px-6 py-2 text-green-700 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          cad_extract.xlsx downloaded successfully.
        </div>
      )}

      {/* Export error banner */}
      {exportMutation.isError && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-2 text-red-700 text-sm">
          Export failed: {String((exportMutation.error as any)?.response?.data?.detail ?? exportMutation.error)}
        </div>
      )}

      {/* No mappings guard */}
      {mappings.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <p className="text-slate-500">No mappings found.</p>
          <Link
            to="/extract/$fileId"
            params={{ fileId }}
            className="text-blue-600 underline text-sm"
          >
            ← Go back and add columns
          </Link>
        </div>
      )}

      {/* Preview table */}
      {mappings.length > 0 && (
        <div className="flex-1 p-6 flex flex-col overflow-hidden">
          <DataPreview
            extraction={extraction}
            mappings={mappings}
            onExport={() => exportMutation.mutate(mappings)}
            isExporting={exportMutation.isPending}
          />
        </div>
      )}
    </div>
  );
}
