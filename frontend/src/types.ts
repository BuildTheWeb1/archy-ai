export type PDFStatus = "uploaded" | "processing" | "ready" | "error";
export type ProjectStatus = "active" | "processing" | "ready" | "error";
export type Confidence = "high" | "medium" | "low";

export interface PDFInfo {
  id: string;
  filename: string;
  status: PDFStatus;
  error: string | null;
  uploaded_at: string | null;
}

export interface ScheduleRow {
  id: string;
  mark: number | null;
  diameter: number;
  steel_type: string;
  count: number;
  length: number;
  total_length: number;
  weight_per_meter: number;
  weight: number;
  confidence: Confidence;
  warnings: string[];
}

export interface Schedule {
  id: string;
  project_id: string;
  status: string;
  rows: ScheduleRow[];
  warnings: string[];
  generated_at: string | null;
  last_edited_at: string | null;
}

export interface Project {
  id: string;
  name: string;
  project_number: string | null;
  beneficiary: string | null;
  location: string | null;
  status: ProjectStatus;
  pdfs: PDFInfo[];
  schedule: Schedule | null;
  created_at: string;
}
