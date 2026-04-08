import { useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";

export function FileUpload() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDrawing(file),
    onSuccess: (data) => {
      navigate({ to: "/drawings/$drawingId", params: { drawingId: data.id } });
    },
  });

  const handleFile = (file: File) => {
    const ext = file.name.toLowerCase();
    if (!ext.endsWith(".dwg") && !ext.endsWith(".dxf")) {
      return;
    }
    upload.mutate(file);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">ArchyAI</h1>
          <p className="text-slate-500 text-base">
            Încarcă un fișier DWG — primești toate planșele ca PDF-uri separate, gata de printat.
          </p>
        </div>

        <div
          className={[
            "border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors",
            dragging
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50",
            upload.isPending ? "pointer-events-none opacity-60" : "",
          ].join(" ")}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".dwg,.dxf"
            className="hidden"
            onChange={onInputChange}
          />

          {upload.isPending ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-600 font-medium">Se încarcă fișierul…</p>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-slate-700 font-semibold mb-1">
                Trage fișierul aici sau <span className="text-blue-600">alege din calculator</span>
              </p>
              <p className="text-slate-400 text-sm">Fișiere .dwg sau .dxf</p>
            </>
          )}
        </div>

        {upload.isError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-700 text-sm">
            {(upload.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
              ?? "Încărcarea a eșuat. Încearcă din nou."}
          </div>
        )}

        <div className="mt-8 grid grid-cols-2 gap-4 text-center">
          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="text-2xl font-bold text-blue-600 mb-1">30s</div>
            <div className="text-slate-500 text-sm">în loc de 2–4 ore manual</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="text-2xl font-bold text-blue-600 mb-1">PDF/A3</div>
            <div className="text-slate-500 text-sm">fiecare planșă separat</div>
          </div>
        </div>
      </div>
    </div>
  );
}
