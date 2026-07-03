import axios from "axios";
import type { BackgroundMode, ProcessingSummary } from "../types/api";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 600000,
});
const formOptions = (mode: BackgroundMode, color: string) => ({
  background_mode: mode,
  background_color: color,
});
export async function uploadImages(
  files: File[],
  mode: BackgroundMode,
  color: string,
  onProgress?: (value: number) => void,
) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  Object.entries(formOptions(mode, color)).forEach(([k, v]) =>
    form.append(k, v),
  );
  const { data } = await api.post<ProcessingSummary>(
    "/api/passport/multiple",
    form,
    {
      onUploadProgress: (e) =>
        onProgress?.(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
    },
  );
  return data;
}
export async function uploadZip(
  file: File,
  mode: BackgroundMode,
  color: string,
  onProgress?: (value: number) => void,
) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(formOptions(mode, color)).forEach(([k, v]) =>
    form.append(k, v),
  );
  const { data } = await api.post<ProcessingSummary>(
    "/api/passport/zip",
    form,
    {
      onUploadProgress: (e) =>
        onProgress?.(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
    },
  );
  return data;
}
export const downloadUrl = (path: string) => `${api.defaults.baseURL}${path}`;
export const downloadAllUrl = () => `${api.defaults.baseURL}/api/download/all`;
export async function cleanup() {
  return api.delete("/api/cleanup");
}
