
import axios from "axios";

export const TOKEN_KEY = "asp_access_token";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000/api/v1",
  timeout: 10000,
});

export async function getCurrentUser(token) {
  const { data } = await api.get("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!["admin", "operator"].includes(data?.role)) {
    throw new Error("Vai trò tài khoản không hợp lệ.");
  }

  return data;
}

export async function loginWithPassword(username, password) {
  const { data } = await api.post("/auth/login", {
    username,
    password,
  });

  const token = data?.access_token;

  if (!token) {
    throw new Error("Backend không trả access token.");
  }

  const user = await getCurrentUser(token);

  return { token, user };
}
