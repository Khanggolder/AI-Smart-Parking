import axios from "axios";
import { TOKEN_KEY } from "./auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 30000,
});

function config(extra = {}) {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  return { ...extra, headers: { Authorization: `Bearer ${token}` } };
}

export async function listCompletedSnapshots(cameraId) {
  const { data } = await api.get("/snapshots", config({
    params: { camera_id: cameraId, job_status: "completed", limit: 1 },
  }));
  return data.items;
}

export async function listSnapshots(params) {
  const { data } = await api.get("/snapshots", config({ params }));
  return data;
}

export async function getSnapshot(id) {
  const { data } = await api.get(`/snapshots/${id}`, config());
  return data;
}

export async function getSnapshotImage(id) {
  const { data } = await api.get(`/snapshots/${id}/image`, config({ responseType: "blob" }));
  return data;
}

export async function getPredictionReviews(predictionId) {
  const { data } = await api.get(`/predictions/${predictionId}/reviews`, config());
  return data;
}

export async function createPredictionReview(predictionId, payload) {
  const { data } = await api.post(`/predictions/${predictionId}/reviews`, payload, config());
  return data;
}

export async function submitSnapshot(cameraId, file, capturedAt) {
  const form = new FormData();
  form.append("camera_id", cameraId);
  form.append("captured_at", capturedAt);
  form.append("image", file);
  const { data } = await api.post("/snapshots", form, config());
  return data;
}
