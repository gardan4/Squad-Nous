const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchSchema() {
  const res = await fetch(`${API_BASE}/api/schema`);
  if (!res.ok) throw new Error("Failed to fetch schema");
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/api/session`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function sendMessage(sessionId: string, message: string) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function closeSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to close session");
  return res.json();
}
