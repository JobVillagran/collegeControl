const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const ACCESS_KEY_STORAGE = "college_control_access_key";

export function getStoredAccessKey() {
  return sessionStorage.getItem(ACCESS_KEY_STORAGE) || "";
}

export function storeAccessKey(value) {
  sessionStorage.setItem(ACCESS_KEY_STORAGE, value);
}

export function clearAccessKey() {
  sessionStorage.removeItem(ACCESS_KEY_STORAGE);
}

async function request(path, options = {}) {
  const accessKey = getStoredAccessKey();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "X-App-Key": accessKey,
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `API error: ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) {
        detail = `${detail} - ${data.detail}`;
      }
    } catch (_) {}
    throw new Error(detail);
  }

  return response.json();
}

export function getDashboard(refresh = false) {
  return request(`/api/dashboard${refresh ? "?refresh=true" : ""}`);
}

export function refreshDashboard() {
  return request("/api/refresh", {
    method: "POST",
  });
}