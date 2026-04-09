import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

interface Props {
  drawingId: string;
}

export function DrawingDetail({ drawingId }: Props) {
  const { data, isError } = useQuery({
    queryKey: ["drawing", drawingId],
    queryFn: () => api.getDrawing(drawingId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "error" ? false : 2000;
    },
  });

  if (isError) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-red-600 font-medium">Nu s-a putut încărca desenul.</p>
        </div>
      </div>
    );
  }

  if (!data || data.status === "processing") {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-700 font-semibold mb-1">Se procesează desenul…</p>
          <p className="text-slate-400 text-sm">
            {data?.filename ?? "Conversia poate dura ~30–60 secunde."}
          </p>
        </div>
      </div>
    );
  }

  if (data.status === "error") {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="max-w-md text-center">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <p className="text-slate-800 font-semibold mb-2">Procesarea a eșuat</p>
          <p className="text-slate-500 text-sm mb-4">{data.filename}</p>
          {data.error && (
            <pre className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-xs text-left overflow-auto">
              {data.error}
            </pre>
          )}
          <a href="/" className="mt-4 inline-block text-blue-600 text-sm hover:underline">
            ← Încearcă alt fișier
          </a>
        </div>
      </div>
    );
  }

  // ready
  const pdfUrl = api.drawingPdfUrl(drawingId);

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Top bar */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <a href="/" className="text-slate-400 hover:text-white text-sm transition-colors">
            ← Încarcă alt fișier
          </a>
          <span className="text-slate-600">|</span>
          <span className="text-slate-200 text-sm font-medium truncate max-w-xs">
            {data.filename}
          </span>
        </div>

        <a
          href={`${pdfUrl}?download=1`}
          download={data.filename.replace(/\.[^.]+$/, ".pdf")}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Descarcă PDF
        </a>
      </div>

      {/* PDF preview */}
      <iframe
        src={pdfUrl}
        className="flex-1 w-full border-0"
        title={data.filename}
      />
    </div>
  );
}
