import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { api } from "../../lib/api";
import { ScheduleTable } from "../../components/ScheduleTable";
import type { ScheduleRow } from "../../types";

export const Route = createFileRoute("/projects/$projectId")({
  component: ProjectDetailPage,
});

function ProjectDetailPage() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rows, setRows] = useState<ScheduleRow[] | null>(null);
  const [dirty, setDirty] = useState(false);

  // ── Project + schedule polling ──────────────────────────────────────────
  const { data: project, isError } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" ? 2000 : false;
    },
  });

  // Sync rows from server when schedule arrives and user has not made edits
  const serverRows = project?.schedule?.rows ?? null;
  if (serverRows !== null && rows === null) {
    setRows(serverRows);
  }

  // ── Upload PDFs ─────────────────────────────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => api.uploadPDFs(projectId, files),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
  });

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    const pdfs = Array.from(fileList).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (pdfs.length === 0) return;
    uploadMutation.mutate(pdfs);
  };

  // ── Trigger extraction ──────────────────────────────────────────────────
  const extractMutation = useMutation({
    mutationFn: () => api.triggerExtraction(projectId),
    onSuccess: () => {
      setRows(null);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  // ── Save edits ──────────────────────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: (r: ScheduleRow[]) => api.updateSchedule(projectId, r),
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const handleRowChange = useCallback((updated: ScheduleRow[]) => {
    setRows(updated);
    setDirty(true);
  }, []);

  if (isError) {
    return (
      <div className="flex items-center justify-center py-32">
        <p className="text-red-600">Nu s-a putut încărca proiectul.</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isProcessing = project.status === "processing";
  const hasPDFs = project.pdfs.length > 0;
  const hasSchedule = !!project.schedule && project.status === "ready";
  const warnings = project.schedule?.warnings ?? [];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 w-full">
      {/* Breadcrumb + title */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
        <Link to="/" className="hover:text-blue-600">Proiecte</Link>
        <span>/</span>
        <span className="text-slate-800 font-medium">{project.name}</span>
      </div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{project.name}</h1>
          {(project.project_number || project.beneficiary || project.location) && (
            <p className="text-sm text-slate-500 mt-0.5">
              {[project.project_number, project.beneficiary, project.location]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>

        {hasSchedule && (
          <a
            href={api.xlsxUrl(projectId)}
            download
            className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Excel
          </a>
        )}
      </div>

      {/* ── Upload zone ────────────────────────────────────────────── */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-2 uppercase tracking-wide">
          Fișiere PDF
        </h2>

        <div
          className={[
            "border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors",
            dragging
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 bg-white hover:border-blue-400",
            uploadMutation.isPending ? "opacity-60 pointer-events-none" : "",
          ].join(" ")}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {uploadMutation.isPending ? (
            <div className="flex items-center justify-center gap-2 py-2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-500 text-sm">Se încarcă fișierele…</p>
            </div>
          ) : (
            <div className="py-2">
              <svg className="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-slate-600 text-sm font-medium">
                Trage fișierele aici sau{" "}
                <span className="text-blue-600 underline underline-offset-2">alege din calculator</span>
              </p>
              <p className="text-slate-400 text-xs mt-1">Selectează mai multe PDF-uri deodată · maxim 10</p>
            </div>
          )}
        </div>

        {uploadMutation.isError && (
          <p className="text-red-600 text-sm mt-2">
            Eroare la încărcare. Verificați că sunt fișiere PDF valide.
          </p>
        )}

        {/* PDF grid */}
        {hasPDFs && (
          <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-5">
            {project.pdfs.map((pdf) => (
              <div
                key={pdf.id}
                className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 min-w-0"
              >
                <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <span className="truncate flex-1 min-w-0">{pdf.filename}</span>
                {pdf.status === "processing" && (
                  <span className="shrink-0 w-3 h-3 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin" />
                )}
                {pdf.status === "error" && (
                  <span className="shrink-0 text-xs text-red-500 font-medium">!</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Extract button ─────────────────────────────────────────── */}
      {hasPDFs && !isProcessing && (
        <div className="mb-8">
          <button
            onClick={() => extractMutation.mutate()}
            disabled={extractMutation.isPending}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {extractMutation.isPending ? "Se pornește…" : hasSchedule ? "Re-extrage armătura" : "Extrage armătura"}
          </button>
          {extractMutation.isError && (
            <p className="text-red-600 text-sm mt-2">Eroare la pornirea extracției.</p>
          )}
        </div>
      )}

      {/* ── Processing state ───────────────────────────────────────── */}
      {isProcessing && (
        <div className="flex items-center gap-3 bg-yellow-50 border border-yellow-200 rounded-xl px-5 py-4 mb-8">
          <div className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin shrink-0" />
          <p className="text-yellow-800 text-sm font-medium">
            Extragere armătură în curs… pagina se va actualiza automat.
          </p>
        </div>
      )}

      {/* ── Error state ────────────────────────────────────────────── */}
      {project.status === "error" && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 mb-8">
          <p className="text-red-700 text-sm font-medium">Extragerea a eșuat.</p>
          {(project as { error?: string }).error && (
            <pre className="text-red-600 text-xs mt-1 whitespace-pre-wrap">
              {(project as { error?: string }).error}
            </pre>
          )}
        </div>
      )}

      {/* ── Schedule ───────────────────────────────────────────────── */}
      {(hasSchedule || (rows && rows.length > 0)) && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Extras de armătură
            </h2>
            {dirty && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Modificări nesalvate</span>
                <button
                  onClick={() => rows && saveMutation.mutate(rows)}
                  disabled={saveMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1.5 rounded text-xs font-medium transition-colors"
                >
                  {saveMutation.isPending ? "Se salvează…" : "Salvează"}
                </button>
              </div>
            )}
          </div>

          {warnings.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 mb-4 space-y-1">
              <p className="text-yellow-800 text-xs font-semibold">Avertismente extracție:</p>
              {warnings.map((w, i) => (
                <p key={i} className="text-yellow-700 text-xs">· {w}</p>
              ))}
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <ScheduleTable
              rows={rows ?? []}
              onChange={handleRowChange}
            />
          </div>
        </section>
      )}

      {/* Empty state — no schedule yet */}
      {!hasSchedule && !isProcessing && hasPDFs && !rows && (
        <div className="text-center py-12 text-slate-400 text-sm">
          Apasă „Extrage armătura" pentru a genera extrasul.
        </div>
      )}

      {!hasPDFs && !isProcessing && (
        <div className="text-center py-12 text-slate-400 text-sm">
          Încarcă cel puțin un fișier PDF pentru a continua.
        </div>
      )}
    </div>
  );
}
