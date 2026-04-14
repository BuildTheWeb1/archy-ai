import axios from "axios";
import type { PDFInfo, Project, Schedule, ScheduleRow } from "../types";

const client = axios.create({ baseURL: "http://localhost:8000" });

export const api = {
  // ── Projects ──────────────────────────────────────────────────────────

  createProject: async (data: {
    name: string;
    project_number?: string;
    beneficiary?: string;
    location?: string;
  }): Promise<Project> => {
    const res = await client.post<Project>("/api/projects", data);
    return res.data;
  },

  listProjects: async (): Promise<Project[]> => {
    const res = await client.get<Project[]>("/api/projects");
    return res.data;
  },

  getProject: async (id: string): Promise<Project> => {
    const res = await client.get<Project>(`/api/projects/${id}`);
    return res.data;
  },

  deleteProject: async (id: string): Promise<void> => {
    await client.delete(`/api/projects/${id}`);
  },

  // ── PDFs ──────────────────────────────────────────────────────────────

  uploadPDFs: async (
    projectId: string,
    files: File[],
  ): Promise<{ uploaded: PDFInfo[] }> => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    const res = await client.post<{ uploaded: PDFInfo[] }>(
      `/api/projects/${projectId}/pdfs`,
      form,
    );
    return res.data;
  },

  // ── Extraction ────────────────────────────────────────────────────────

  triggerExtraction: async (projectId: string): Promise<void> => {
    await client.post(`/api/projects/${projectId}/extract`);
  },

  // ── Schedule ──────────────────────────────────────────────────────────

  getSchedule: async (projectId: string): Promise<Schedule> => {
    const res = await client.get<Schedule>(`/api/projects/${projectId}/schedule`);
    return res.data;
  },

  updateSchedule: async (
    projectId: string,
    rows: ScheduleRow[],
  ): Promise<Schedule> => {
    const res = await client.put<Schedule>(
      `/api/projects/${projectId}/schedule`,
      { rows },
    );
    return res.data;
  },

  xlsxUrl: (projectId: string): string =>
    `http://localhost:8000/api/projects/${projectId}/schedule/xlsx`,
};
