
import axios from "axios";
import { TOKEN_KEY } from "./auth";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000/api/v1",
  timeout: 10000,
});

// GET ảnh tham chiếu từ Backend bằng JWT
export async function fetchCameraReferenceImage(cameraId) {
  const token = sessionStorage.getItem(TOKEN_KEY);

  if (!token) {
    throw new Error("Bạn cần đăng nhập để tải ảnh.");
  }

  const { data } = await api.get(
    `/cameras/${cameraId}/reference-image`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      responseType: "blob",
    }
  );

  return data;
}

export async function uploadCameraReferenceImage(
  cameraId,
  file,
  cameraVersion
) {
  const token = sessionStorage.getItem(TOKEN_KEY);

  if (!token) {
    throw new Error("Bạn cần đăng nhập để upload ảnh.");
  }

  const formData = new FormData();

  formData.append("image", file);
  formData.append(
    "expected_camera_config_version",
    String(cameraVersion)
  );

  const { data } = await api.put(
    `/cameras/${cameraId}/reference-image`,
    formData,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      timeout: 30000,
    }
  );

  return data;
}
