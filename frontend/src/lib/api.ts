import axios from "axios";
import type { Drawing, UploadResponse } from "../types";

const client = axios.create({ baseURL: "http://localhost:8000" });

export const api = {
  uploadDrawing: async (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    const res = await client.post<UploadResponse>("/api/drawings/upload", form);
    return res.data;
  },

  getDrawing: async (id: string): Promise<Drawing> => {
    const res = await client.get<Drawing>(`/api/drawings/${id}`);
    return res.data;
  },

  drawingPdfUrl: (drawingId: string): string =>
    `http://localhost:8000/api/drawings/${drawingId}/pdf`,
};
