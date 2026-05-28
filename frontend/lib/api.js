const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  let token = null;
  if (typeof window !== "undefined") {
    token = localStorage.getItem("paklaw_token");
  }

  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {})
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("paklaw_token");
    }
    throw new Error(data?.detail || "Request failed");
  }

  return data;
}

export async function login(username, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
  if (data && data.access_token && typeof window !== "undefined") {
    localStorage.setItem("paklaw_token", data.access_token);
  }
  return data;
}

export async function signup(username, password, firmId) {
  const data = await apiFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, password, firm_id: firmId })
  });
  if (data && data.access_token && typeof window !== "undefined") {
    localStorage.setItem("paklaw_token", data.access_token);
  }
  return data;
}

export async function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("paklaw_token");
  }
  return apiFetch("/auth/logout", { method: "POST" });
}

export function getMe() {
  return apiFetch("/user/me");
}

export function runSearch(mode, payload) {
  return apiFetch(`/search/${mode}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function uploadFirmPdf({ file, firmId, accessLevel }) {
  const body = new FormData();
  body.append("file", file);
  body.append("firm_id", firmId);
  body.append("access_level", accessLevel);

  return apiFetch("/ingest/firm", {
    method: "POST",
    body
  });
}
