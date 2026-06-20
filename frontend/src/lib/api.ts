/**
 * API client for fufan OpenClaw backend.
 * Custom SSE parser for POST requests (native EventSource only supports GET).
 */

const API_BASE =
  typeof window !== "undefined"
    ? `http://${window.location.hostname}:8002/api`
    : "http://localhost:8002/api";

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * Stream chat messages via POST SSE.
 * Yields parsed SSE events as they arrive.
 */
export async function* streamChat(
  message: string,
  sessionId: string
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`Chat API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "message";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const dataStr = line.slice(5).trim();
        if (dataStr) {
          try {
            const data = JSON.parse(dataStr);
            yield { event: currentEvent, data };
          } catch {
            // Skip malformed JSON
          }
        }
      }
      // Empty line resets event type
      if (line === "") {
        currentEvent = "message";
      }
    }
  }
}

/**
 * Read a file from the backend.
 */
export async function readFile(path: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/files?path=${encodeURIComponent(path)}`);
  if (!resp.ok) throw new Error(`Failed to read file: ${resp.status}`);
  const data = await resp.json();
  return data.content;
}

/**
 * Save a file to the backend.
 */
export async function saveFile(path: string, content: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!resp.ok) throw new Error(`Failed to save file: ${resp.status}`);
}

/**
 * List all sessions.
 */
export async function listSessions(): Promise<
  Array<{ id: string; title: string; updated_at: number }>
> {
  const resp = await fetch(`${API_BASE}/sessions`);
  if (!resp.ok) throw new Error(`Failed to list sessions: ${resp.status}`);
  const data = await resp.json();
  return data.sessions;
}

/**
 * Create a new session.
 */
export async function createSession(): Promise<{ id: string; title: string }> {
  const resp = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!resp.ok) throw new Error(`Failed to create session: ${resp.status}`);
  return resp.json();
}

/**
 * Rename a session.
 */
export async function renameSession(id: string, title: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!resp.ok) throw new Error(`Failed to rename session: ${resp.status}`);
}

/**
 * Delete a session.
 */
export async function deleteSession(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/sessions/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw new Error(`Failed to delete session: ${resp.status}`);
}

/**
 * Get raw messages for a session (including system prompt).
 */
export async function getRawMessages(
  sessionId: string
): Promise<{ session_id: string; title: string; messages: Array<{ role: string; content: string }> }> {
  const resp = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/messages`
  );
  if (!resp.ok) throw new Error(`Failed to get raw messages: ${resp.status}`);
  return resp.json();
}

/**
 * Get session conversation history (no system prompt, includes tool_calls).
 */
export async function getSessionHistory(
  sessionId: string
): Promise<{
  session_id: string;
  messages: Array<{ role: string; content: string; tool_calls?: Array<{ tool: string; input?: string; output?: string }> }>;
}> {
  const resp = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/history`
  );
  if (!resp.ok) throw new Error(`Failed to get session history: ${resp.status}`);
  return resp.json();
}

/**
 * List available skills.
 */
export async function listSkills(): Promise<
  Array<{ name: string; path: string; description: string }>
> {
  const resp = await fetch(`${API_BASE}/skills`);
  if (!resp.ok) throw new Error(`Failed to list skills: ${resp.status}`);
  const data = await resp.json();
  return data.skills;
}

/**
 * Generate a title for a session using AI.
 */
export async function generateTitle(
  sessionId: string
): Promise<{ title: string }> {
  const resp = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/generate-title`,
    { method: "POST" }
  );
  if (!resp.ok) throw new Error(`Failed to generate title: ${resp.status}`);
  return resp.json();
}

/**
 * Get token count for a session (system + messages).
 */
export async function getSessionTokenCount(
  sessionId: string
): Promise<{ system_tokens: number; message_tokens: number; total_tokens: number }> {
  const resp = await fetch(
    `${API_BASE}/tokens/session/${encodeURIComponent(sessionId)}`
  );
  if (!resp.ok) throw new Error(`Failed to get token count: ${resp.status}`);
  return resp.json();
}

/**
 * Get token counts for a list of files.
 */
export async function getFileTokenCounts(
  paths: string[]
): Promise<{ files: Array<{ path: string; tokens: number }> }> {
  const resp = await fetch(`${API_BASE}/tokens/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paths }),
  });
  if (!resp.ok) throw new Error(`Failed to get file token counts: ${resp.status}`);
  return resp.json();
}

/**
 * Compress a session's conversation history.
 */
export async function compressSession(
  sessionId: string
): Promise<{ archived_count: number; remaining_count: number }> {
  const resp = await fetch(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/compress`,
    { method: "POST" }
  );
  if (!resp.ok) throw new Error(`Failed to compress session: ${resp.status}`);
  return resp.json();
}

/**
 * Get current RAG mode status.
 */
export async function getRagMode(): Promise<{ rag_mode: boolean }> {
  const resp = await fetch(`${API_BASE}/config/rag-mode`);
  if (!resp.ok) throw new Error(`Failed to get RAG mode: ${resp.status}`);
  return resp.json();
}

/**
 * Set RAG mode enabled/disabled.
 */
export async function setRagMode(
  enabled: boolean
): Promise<{ rag_mode: boolean }> {
  const resp = await fetch(`${API_BASE}/config/rag-mode`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!resp.ok) throw new Error(`Failed to set RAG mode: ${resp.status}`);
  return resp.json();
}

/**
 * Delete a skill by name.
 */
export async function deleteSkill(name: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/skills/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw new Error(`Failed to delete skill: ${resp.status}`);
}

/**
 * Get masked API keys from backend.
 */
export async function getApiKeys(): Promise<Record<string, string>> {
  const resp = await fetch(`${API_BASE}/config/api-keys`);
  if (!resp.ok) throw new Error(`Failed to get API keys: ${resp.status}`);
  return resp.json();
}

/**
 * Update API keys on backend.
 */
export async function setApiKeys(keys: Record<string, string>): Promise<Record<string, string>> {
  const resp = await fetch(`${API_BASE}/config/api-keys`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
  if (!resp.ok) throw new Error(`Failed to set API keys: ${resp.status}`);
  return resp.json();
}

/**
 * Create a new skill template (SKILL.md) at skills/{name}/SKILL.md.
 */
export async function createSkillTemplate(
  name: string,
  content: string
): Promise<void> {
  await saveFile(`skills/${name}/SKILL.md`, content);
}

/**
 * Stream chat and collect full response text.
 * Calls onToken for each streamed token, onToolStart/onToolEnd for tool events.
 * Returns the full accumulated text when done.
 */
export async function streamChatCollect(
  message: string,
  sessionId: string,
  callbacks?: {
    onToken?: (text: string) => void;
    onToolStart?: (tool: string, input: string) => void;
    onToolEnd?: (tool: string, output: string) => void;
    onError?: (error: string) => void;
  }
): Promise<string> {
  let fullText = "";
  for await (const event of streamChat(message, sessionId)) {
    if (event.event === "token") {
      const content = (event.data.content as string) || "";
      fullText += content;
      callbacks?.onToken?.(content);
    } else if (event.event === "tool_start") {
      callbacks?.onToolStart?.(event.data.tool as string, event.data.input as string);
    } else if (event.event === "tool_end") {
      callbacks?.onToolEnd?.(event.data.tool as string, event.data.output as string);
    } else if (event.event === "error") {
      callbacks?.onError?.((event.data.error as string) || "Unknown error");
      break;
    } else if (event.event === "done") {
      break;
    }
  }
  return fullText;
}
