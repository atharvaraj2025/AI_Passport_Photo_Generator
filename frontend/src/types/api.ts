export type BackgroundMode = "original" | "solid";
export interface ProcessedPhoto {
  original_filename: string;
  output_filename: string;
  download_url: string;
  width: number;
  height: number;
  faces_detected: number;
  background_mode: BackgroundMode;
}
export interface ErrorDetail {
  filename?: string;
  message: string;
  code: string;
}
export interface ProcessingSummary {
  total: number;
  successful: number;
  failed: number;
  elapsed_seconds: number;
  results: ProcessedPhoto[];
  errors: ErrorDetail[];
}
export interface SessionItem extends ProcessedPhoto {
  id: string;
  createdAt: string;
}
