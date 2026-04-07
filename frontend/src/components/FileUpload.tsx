import { useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useUpload } from "../hooks/useExtraction";

export function FileUpload() {
  const navigate = useNavigate();
  const upload = useUpload();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    upload.mutate(file, {
      onSuccess: (data) => {
        navigate({ to: "/sheets/$fileId", params: { fileId: data.id } });
      },
    });
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
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Archy AI</h1>
          <p className="text-slate-500 text-base">
            Upload a DWG or DXF file to export each sheet as an A3 PDF
          </p>
        </div>

        {/* Drop zone */}
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
            accept=".dxf,.dwg"
            className="hidden"
            onChange={onInputChange}
          />

          {upload.isPending ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-600 font-medium">Extracting data…</p>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-slate-700 font-semibold mb-1">
                Drop your file here or <span className="text-blue-600">browse</span>
              </p>
              <p className="text-slate-400 text-sm">Supports .dwg and .dxf files</p>
            </>
          )}
        </div>

        {/* Error */}
        {upload.isError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-700 text-sm">
            {(upload.error as any)?.response?.data?.detail ?? "Upload failed. Please try again."}
          </div>
        )}

        {/* Info */}
        <p className="text-center text-slate-400 text-xs mt-6">
          Files are processed locally — nothing leaves your machine.
        </p>
      </div>
    </div>
  );
}
