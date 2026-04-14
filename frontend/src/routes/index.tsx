import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import type { Project } from "../types";

export const Route = createFileRoute("/")({
  component: ProjectsPage,
});

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ro-RO", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

function StatusBadge({ status }: { status: Project["status"] }) {
  const map = {
    active: "bg-slate-100 text-slate-600",
    processing: "bg-yellow-100 text-yellow-700",
    ready: "bg-green-100 text-green-700",
    error: "bg-red-100 text-red-700",
  };
  const label = {
    active: "Activ", processing: "Procesare…", ready: "Gata", error: "Eroare",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${map[status]}`}>
      {label[status]}
    </span>
  );
}

function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "", project_number: "", beneficiary: "", location: "",
  });

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  const createMutation = useMutation({
    mutationFn: api.createProject,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setFormData({ name: "", project_number: "", beneficiary: "", location: "" });
      navigate({ to: "/projects/$projectId", params: { projectId: project.id } });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    createMutation.mutate({
      name: formData.name.trim(),
      project_number: formData.project_number.trim() || undefined,
      beneficiary: formData.beneficiary.trim() || undefined,
      location: formData.location.trim() || undefined,
    });
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Proiecte</h1>
          <p className="text-slate-500 text-sm mt-1">
            Gestionează extrasele de armătură din planuri PDF.
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          + Proiect nou
        </button>
      </div>

      {/* New project form */}
      {showForm && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-4">Proiect nou</h2>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Denumire proiect *
                </label>
                <input
                  autoFocus
                  value={formData.name}
                  onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                  placeholder="ex: Bloc A3 — fundații"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Nr. proiect</label>
                <input
                  value={formData.project_number}
                  onChange={(e) => setFormData((f) => ({ ...f, project_number: e.target.value }))}
                  placeholder="ex: P-2024-042"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Beneficiar</label>
                <input
                  value={formData.beneficiary}
                  onChange={(e) => setFormData((f) => ({ ...f, beneficiary: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Locație</label>
                <input
                  value={formData.location}
                  onChange={(e) => setFormData((f) => ({ ...f, location: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                disabled={!formData.name.trim() || createMutation.isPending}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {createMutation.isPending ? "Se creează…" : "Creează proiect"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-sm"
              >
                Anulează
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Project list */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-400">Se încarcă…</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-slate-600 font-medium">Niciun proiect creat</p>
          <p className="text-slate-400 text-sm mt-1">Creează primul proiect pentru a începe.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white border border-slate-200 rounded-xl px-5 py-4 flex items-center justify-between hover:border-blue-300 transition-colors cursor-pointer group"
              onClick={() =>
                navigate({ to: "/projects/$projectId", params: { projectId: project.id } })
              }
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
                    {project.name}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {project.project_number && <span className="mr-2">{project.project_number}</span>}
                    {project.pdfs.length} PDF{project.pdfs.length !== 1 ? "-uri" : ""}
                    {" · "}{formatDate(project.created_at)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <StatusBadge status={project.status} />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Ștergi proiectul „${project.name}"?`))
                      deleteMutation.mutate(project.id);
                  }}
                  className="text-slate-300 hover:text-red-500 transition-colors text-lg leading-none"
                  title="Șterge proiect"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
