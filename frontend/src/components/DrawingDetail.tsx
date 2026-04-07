import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LayoutList } from "./LayoutList";

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
            {data?.filename ?? "Se convertește via CloudConvert, poate dura ~30 secunde."}
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
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href="/" className="text-blue-600 text-sm hover:underline mb-1 block">
              ← Încarcă alt fișier
            </a>
            <h1 className="text-2xl font-bold text-slate-900">{data.filename}</h1>
            <p className="text-slate-500 text-sm mt-1">
              {data.layouts.length} planș{data.layouts.length === 1 ? "ă" : "e"} extrase
            </p>
          </div>
          <a
            href={api.downloadAllUrl(drawingId)}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Descarcă tot (.zip)
          </a>
        </div>

        <LayoutList drawingId={drawingId} layouts={data.layouts} />
      </div>
    </div>
  );
}
