
import axios from "axios";
import { TOKEN_KEY } from "./auth";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000/api/v1",
  timeout: 10000,
});

function authConfig() {
  const token = sessionStorage.getItem(TOKEN_KEY);

  if (!token) {
    throw new Error("Bạn cần đăng nhập để sử dụng API Polygon.");
  }

  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };
}

// GET: lấy danh sách polygon của một camera
export async function fetchCameraSpots(cameraId) {
  const { data } = await api.get(
    `/cameras/${cameraId}/spots`,
    authConfig()
  );

  return data;
}

// POST: tạo polygon mới
export async function createSpot(
  cameraId,
  spotCode,
  polygon,
  cameraVersion
) {
  const { data } = await api.post(
    `/cameras/${cameraId}/spots`,
    {
      spot_code: spotCode,
      polygon,
      expected_camera_config_version: cameraVersion,
    },
    authConfig()
  );

  return data;
}

// PATCH: chỉnh sửa tọa độ polygon
export async function updateSpot(
  spotId,
  polygon,
  cameraVersion
) {
  const { data } = await api.patch(
    `/spots/${spotId}`,
    {
      polygon,
      expected_camera_config_version: cameraVersion,
    },
    authConfig()
  );

  return data;
}

// DELETE: ngừng kích hoạt polygon
export async function deleteSpot(
  spotId,
  cameraVersion
) {
  await api.delete(`/spots/${spotId}`, {
    ...authConfig(),
    params: {
      expected_camera_config_version: cameraVersion,
    },
  });
}
