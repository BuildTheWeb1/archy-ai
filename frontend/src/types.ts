export type DrawingStatus = "uploading" | "processing" | "ready" | "error";

export interface Layout {
  index: number;
  name: string;
}

export interface Drawing {
  id: string;
  filename: string;
  status: DrawingStatus;
  error: string | null;
  layouts: Layout[];
}

export interface UploadResponse {
  id: string;
  status: DrawingStatus;
}
