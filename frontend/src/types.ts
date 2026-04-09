export type DrawingStatus = "uploading" | "processing" | "ready" | "error";

export interface Drawing {
  id:       string;
  filename: string;
  status:   DrawingStatus;
  error:    string | null;
}

export interface UploadResponse {
  id:     string;
  status: DrawingStatus;
}
