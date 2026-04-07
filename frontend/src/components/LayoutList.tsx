import type { Layout } from "../types";
import { api } from "../lib/api";

interface Props {
  drawingId: string;
  layouts: Layout[];
}

export function LayoutList({ drawingId, layouts }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {layouts.map((layout) => (
        <LayoutCard key={layout.index} drawingId={drawingId} layout={layout} />
      ))}
    </div>
  );
}

function LayoutCard({ drawingId, layout }: { drawingId: string; layout: Layout }) {
  const pdfUrl = api.layoutPdfUrl(drawingId, layout.index);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-3 hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-400 font-medium mb-0.5">
            Planșa {layout.index + 1}
          </p>
          <p className="text-slate-800 font-semibold text-sm leading-snug truncate">
            {layout.name}
          </p>
        </div>
        <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd"
              d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
              clipRule="evenodd" />
          </svg>
        </div>
      </div>

      <a
        href={pdfUrl}
        download
        className="inline-flex items-center justify-center gap-2 w-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Descarcă PDF
      </a>
    </div>
  );
}
