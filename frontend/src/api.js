/**
 * Thin fetch wrapper for the backend API.
 * Base URL is empty because Vite dev server proxies /api -> backend.
 */

const BASE = "/api";

async function handleJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${BASE}/chat/session`, { method: "POST" });
  return handleJson(res);
}

export async function listSources(sessionId) {
  const res = await fetch(`${BASE}/sources/${sessionId}`);
  return handleJson(res);
}

export async function uploadFileSource(kind, sessionId, file) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);
  const res = await fetch(`${BASE}/sources/${kind}`, { method: "POST", body: form });
  return handleJson(res);
}

export async function addUrlSource(kind, sessionId, url) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("url", url);
  const res = await fetch(`${BASE}/sources/${kind}`, { method: "POST", body: form });
  return handleJson(res);
}

export async function removeSource(sessionId, sourceId) {
  const res = await fetch(`${BASE}/sources/${sessionId}/${sourceId}`, { method: "DELETE" });
  return handleJson(res);
}

export async function generateQuiz(sessionId, numQuestions, sourceId) {
  const res = await fetch(`${BASE}/chat/quiz`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, num_questions: numQuestions, source_id: sourceId || null }),
  });
  return handleJson(res);
}

/**
 * Streams a chat response via Server-Sent Events.
 * Calls onToken(text) for each token, and onDone(citations) at the end.
 * Returns nothing; throws on network/HTTP error.
 */
export async function streamChat({ sessionId, message, mode, onToken, onDone, onError }) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, mode }),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    onError?.(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // keep incomplete chunk

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.type === "token") {
        onToken(payload.content);
      } else if (payload.type === "done") {
        onDone(payload.citations || []);
      } else if (payload.type === "error") {
        onError?.(payload.content);
      }
    }
  }
}
