// API client for Agent Experts — AI Earning Machine.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AGENT_TOKEN = "agent-secret";

// Store owner token in localStorage
let _ownerToken: string | null = null;
if (typeof window !== "undefined") {
  _ownerToken = localStorage.getItem("owner_token");
}

export function setOwnerToken(token: string) {
  _ownerToken = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("owner_token", token);
  }
}

export function getOwnerToken(): string | null {
  return _ownerToken;
}

export function clearOwnerToken() {
  _ownerToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("owner_token");
  }
}

// --- Auth ---

export async function login(password: string) {
  const res = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  setOwnerToken(data.token);
  return data;
}

export async function autoLogin() {
  // Personal mode: no password needed, get token automatically
  try {
    const res = await fetch(`${API_URL}/auto-login`);
    if (!res.ok) throw new Error("Auto login failed");
    const data = await res.json();
    setOwnerToken(data.token);
    return data.token;
  } catch (e) {
    // Fallback: try password login with default
    try {
      return await login("change123");
    } catch (e2) {
      throw new Error("Auto login failed");
    }
  }
}

// --- Agent Chat ---

export async function chat(message: string) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Agent-Token": AGENT_TOKEN },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Chat failed");
  const data = await res.json();
  return data.reply;
}

// --- Owner API calls (auto-includes auth token) ---

async function authHeaders(): Promise<HeadersInit> {
  const token = getOwnerToken();
  if (!token) return { "Content-Type": "application/json" };
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function apiGet(path: string) {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}${path}`, { headers });
  if (!res.ok) {
    if (res.status === 401) clearOwnerToken();
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return await res.json();
}

export async function apiPost(path: string, body: any) {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    if (res.status === 401) clearOwnerToken();
    const detail = await res.text();
    throw new Error(detail || `POST ${path} failed: ${res.status}`);
  }
  return await res.json();
}