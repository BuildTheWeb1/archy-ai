import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import type {
  ExtractionResult,
  LayerSummary,
  MappingItem,
  SheetsResponse,
  UploadResponse,
} from "../types";

const API = "http://localhost:8000/api";

export function useUpload() {
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await axios.post<UploadResponse>(`${API}/upload`, form);
      return data;
    },
  });
}

export function useExtraction(fileId: string | null) {
  return useQuery({
    queryKey: ["extraction", fileId],
    queryFn: async () => {
      const { data } = await axios.get<ExtractionResult>(
        `${API}/extractions/${fileId}`
      );
      return data;
    },
    enabled: !!fileId,
  });
}

export function useLayers(fileId: string | null) {
  return useQuery({
    queryKey: ["layers", fileId],
    queryFn: async () => {
      const { data } = await axios.get<LayerSummary>(
        `${API}/extractions/${fileId}/layers`
      );
      return data;
    },
    enabled: !!fileId,
  });
}

export function useSheets(fileId: string | null) {
  return useQuery({
    queryKey: ["sheets", fileId],
    queryFn: async () => {
      const { data } = await axios.get<SheetsResponse>(
        `${API}/extractions/${fileId}/sheets`
      );
      return data;
    },
    enabled: !!fileId,
  });
}

export function useDownloadSheetPdf() {
  return useMutation({
    mutationFn: async ({ fileId, pageIndex, sheetName }: { fileId: string; pageIndex: number; sheetName: string }) => {
      const { data } = await axios.get(
        `${API}/extractions/${fileId}/sheets/${pageIndex}/pdf`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${sheetName}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useDownloadAllSheetsPdf(fileId: string | null) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await axios.get(
        `${API}/extractions/${fileId}/sheets-zip`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sheets.zip";
      a.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useExport(fileId: string | null) {
  return useMutation({
    mutationFn: async (mappings: MappingItem[]) => {
      const { data } = await axios.post(
        `${API}/extractions/${fileId}/export`,
        { mappings },
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "cad_extract.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    },
  });
}
