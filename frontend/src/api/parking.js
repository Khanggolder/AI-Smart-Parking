
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

  return {
    headers: {
      Authorization: `Bearer ${token || ""}`,
    },
  };
}

function listData(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  throw new Error("Dữ liệu danh sách từ Backend không hợp lệ.");
}

// Parking Lots
export async function fetchParkingLots() {
  const { data } = await api.get("/parking-lots", authConfig());
  return listData(data);
}

export async function createParkingLot(payload) {
  const { data } = await api.post(
    "/parking-lots",
    payload,
    authConfig()
  );
  return data;
}

export async function updateParkingLot(id, payload) {
  const { data } = await api.patch(
    `/parking-lots/${id}`,
    payload,
    authConfig()
  );
  return data;
}

// Cameras
export async function fetchCameras(parkingLotId) {
  const { data } = await api.get("/cameras", {
    ...authConfig(),
    params: { parking_lot_id: parkingLotId },
  });
  return listData(data);
}

export async function createCamera(payload) {
  const { data } = await api.post(
    "/cameras",
    payload,
    authConfig()
  );
  return data;
}

export async function updateCamera(id, payload) {
  const { data } = await api.patch(
    `/cameras/${id}`,
    payload,
    authConfig()
  );
  return data;
}
