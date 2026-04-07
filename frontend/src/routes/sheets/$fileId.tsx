import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  useSheets,
  useExtraction,
  useDownloadSheetPdf,
  useDownloadAllSheetsPdf,
} from "../../hooks/useExtraction";
import type { Sheet } from "../../types";

export const Route = createFileRoute("/sheets/$fileId")({
  component: SheetsPage,
});

function SheetsPage() {
  const { fileId } = Route.useParams();
  const { data: extraction } = useExtraction(fileId);
  const { data: sheetsData, isLoading, isError } = useSheets(fileId);
  const downloadSheet = useDownloadSheetPdf();
  const downloadAll = useDownloadAllSheetsPdf(fileId);
  const [downloadingSheet, setDownloadingSheet] = useState<string | null>(null);

  const sheets = sheetsData?.sheets ?? [];
  const paperspaceSheets = sheets.filter((s) => s.is_paperspace);
  const displaySheets = paperspaceSheets.length > 0 ? paperspaceSheets : sheets;

  const handleDownloadSheet = (sheet: Sheet, index: number) => {
    setDownloadingSheet(sheet.name);
    const pageIndex = sheet.page_index ?? index;
    downloadSheet.mutate(
      { fileId, pageIndex, sheetName: sheet.name },
      { onSettled: () => setDownloadingSheet(null) }
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-slate-900">
            {extraction?.original_filename ?? extraction?.filename ?? "Drawing"}
          </h1>
          <p className="text-xs text-slate-400">
            {isLoading
              ? "Loading sheets…"
              : `${displaySheets.length} sheet${displaySheets.length !== 1 ? "s" : ""} · A3 PDF export`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/" className="text-sm text-slate-500 hover:text-slate-700">
            ← New file
          </Link>
          <button
            onClick={() => downloadAll.mutate()}
            disabled={downloadAll.isPending || displaySheets.length === 0}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors"
          >
            {downloadAll.isPending ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                Generating…
              </>
            ) : (
              <>
                <DownloadIcon className="w-4 h-4" />
                Export All ({displaySheets.length})
              </>
            )}
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 p-6">
        {isLoading && (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isError && (
          <div className="flex items-center justify-center h-64 text-red-600 text-sm">
            Failed to load sheets.{" "}
            <Link to="/" className="ml-2 underline">
              Try again
            </Link>
          </div>
        )}

        {!isLoading && !isError && displaySheets.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-500 text-sm gap-2">
            <p>No paper-space layouts found in this drawing.</p>
            <p className="text-slate-400 text-xs">
              The file may only contain model space geometry.
            </p>
          </div>
        )}

        {!isLoading && displaySheets.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {displaySheets.map((sheet, index) => (
              <SheetCard
                key={sheet.name}
                sheet={sheet}
                isDownloading={downloadingSheet === sheet.name}
                onDownload={() => handleDownloadSheet(sheet, index)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SheetCard({
  sheet,
  isDownloading,
  onDownload,
}: {
  sheet: Sheet;
  isDownloading: boolean;
  onDownload: () => void;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col">
      {/* Preview placeholder — A3 aspect ratio (297:420 ≈ 0.707) */}
      <div
        className="w-full bg-slate-100 flex items-center justify-center"
        style={{ aspectRatio: "420 / 297" }}
      >
        <div className="flex flex-col items-center gap-2 text-slate-400">
          <FileIcon className="w-10 h-10" />
          <span className="text-xs font-medium">A3 PDF</span>
        </div>
      </div>

      {/* Info + action */}
      <div className="p-3 flex items-start justify-between gap-2 border-t border-slate-100">
        <div className="min-w-0">
          <p
            className="text-sm font-semibold text-slate-800 truncate"
            title={sheet.name}
          >
            {sheet.name}
          </p>
          {sheet.entity_count != null && (
            <p className="text-xs text-slate-400 mt-0.5">
              {sheet.entity_count} entities
            </p>
          )}
        </div>
        <button
          onClick={onDownload}
          disabled={isDownloading}
          className="shrink-0 flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          {isDownloading ? (
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
          ) : (
            <DownloadIcon className="w-3.5 h-3.5" />
          )}
          PDF
        </button>
      </div>
    </div>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}

function FileIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
      />
    </svg>
  );
}
