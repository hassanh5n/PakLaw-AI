const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.detail || "Request failed");
  }

  return data;
}

export function login(username, password) {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export function signup(username, password, firmId) {
  return apiFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, password, firm_id: firmId })
  });
}

export function logout() {
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
