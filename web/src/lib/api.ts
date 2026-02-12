const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("tc_token");
}

export function setToken(token: string) {
  localStorage.setItem("tc_token", token);
}

export function clearToken() {
  localStorage.removeItem("tc_token");
}


export async function api<T>(
  path: string,
  method: "GET" | "POST" = "GET",
  body?: unknown,
  needAuth: boolean = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (needAuth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
