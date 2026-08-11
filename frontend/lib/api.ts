// Simple API client for Agent Experts backend.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AGENT_TOKEN = "agent-secret"; // set this to match backend AGENT_TOKEN env

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

// Card/panel data endpoints are opened (auth removed), so no token needed.
export async function apiGet(path: string, _token?: string) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Request failed");
  }
  return await res.json();
}

export async function apiPost(path: string, body: any, _token?: string) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Request failed");
  }
  return await res.json();
}
