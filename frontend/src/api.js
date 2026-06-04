const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export function getDashboard(refresh = false) {
  return request(`/api/dashboard${refresh ? "?refresh=true" : ""}`);
}

export function refreshDashboard() {
  return request("/api/refresh", { method: "POST" });
}