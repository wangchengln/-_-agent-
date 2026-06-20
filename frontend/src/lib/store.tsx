"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from "react";
import {
  streamChat,
  listSessions as apiListSessions,
  createSession as apiCreateSession,
  renameSession as apiRenameSession,
  deleteSession as apiDeleteSession,
  getRawMessages as apiGetRawMessages,
  getSessionHistory as apiGetSessionHistory,
  compressSession as apiCompressSession,
  getRagMode as apiGetRagMode,
  setRagMode as apiSetRagMode,
} from "./api";

// ── Types ──────────────────────────────────────────────────

export interface ToolCall {
  tool: string;
  input?: string;
  output?: string;
  status: "running" | "done";
}

export interface RetrievalResult {
  text: string;
  score: string;
  source: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  retrievals?: RetrievalResult[];
  timestamp: number;
}

export interface SessionMeta {
  id: string;
  title: string;
  updated_at: number;
}

export interface RawMessage {
  role: string;
  content: string;
  tool_calls?: Array<{ tool: string; input?: string; output?: string }>;
}

interface AppState {
  // Chat
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (text: string) => Promise<void>;

  // Sessions
  sessionId: string;
  setSessionId: (id: string) => void;
  sessions: SessionMeta[];
  loadSessions: () => void;
  createSession: () => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;

  // Sidebar
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Raw messages
  rawMessages: RawMessage[] | null;
  loadRawMessages: () => void;

  // Compression
  isCompressing: boolean;
  compressCurrentSession: () => Promise<void>;

  // RAG mode
  ragMode: boolean;
  toggleRagMode: () => void;

  // Canvas
  canvasCode: string;
  canvasReady: boolean;
  canvasStreaming: boolean;
  setCanvasCode: (code: string) => void;
  setCanvasReady: (ready: boolean) => void;
  resetCanvas: () => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionIdRaw] = useState("default");
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rawMessages, setRawMessages] = useState<RawMessage[] | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);
  const [ragMode, setRagMode] = useState(false);
  const [canvasCode, setCanvasCode] = useState("");
  const [canvasReady, setCanvasReady] = useState(false);
  const [canvasStreaming, setCanvasStreaming] = useState(false);
  const canvasBufferRef = useRef("");
  const inCanvasRef = useRef(false);
  const abortRef = useRef(false);

  // ── Ghost session management ──────────────────────────
  // A "ghost" is a session created on the backend but not shown in the sidebar.
  // It becomes visible only when the backend sends a `title` event (first response).
  const ghostSessionRef = useRef<string | null>(null);
  const titleAnimTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** Silently delete the current ghost session from the backend. */
  const cleanupGhost = useCallback(() => {
    const ghostId = ghostSessionRef.current;
    if (ghostId) {
      ghostSessionRef.current = null;
      apiDeleteSession(ghostId).catch(() => {});
    }
  }, []);

  /** Create a new ghost session: active but invisible in sidebar. */
  const spawnGhost = useCallback(() => {
    apiCreateSession()
      .then((meta) => {
        ghostSessionRef.current = meta.id;
        setSessionIdRaw(meta.id);
        setMessages([]);
        setRawMessages(null);
      })
      .catch(() => {});
  }, []);

  const resetCanvas = useCallback(() => {
    setCanvasCode("");
    setCanvasReady(false);
    setCanvasStreaming(false);
    canvasBufferRef.current = "";
    inCanvasRef.current = false;
  }, []);

  // Load RAG mode on mount
  useEffect(() => {
    apiGetRagMode()
      .then((data) => setRagMode(data.rag_mode))
      .catch(() => {});
  }, []);

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);

  // ── Session management ─────────────────────────────

  const loadSessions = useCallback(() => {
    apiListSessions()
      .then((list) => {
        const ghostId = ghostSessionRef.current;
        // Filter out: 1) the current ghost session  2) any "New Chat" titled sessions (orphans)
        setSessions(
          list.filter((s) => s.id !== ghostId && s.title !== "New Chat")
        );
      })
      .catch(() => {});
  }, []);

  // On mount: purge orphan "New Chat" sessions left by previous page loads, then spawn ghost
  useEffect(() => {
    apiListSessions()
      .then((list) => {
        const orphans = list.filter((s) => s.title === "New Chat");
        // Delete orphans from backend silently
        for (const o of orphans) {
          apiDeleteSession(o.id).catch(() => {});
        }
        // Show only real sessions
        setSessions(list.filter((s) => s.title !== "New Chat"));
      })
      .catch(() => {});
    spawnGhost();
  }, [spawnGhost]);

  // Cleanup ghost on page close / refresh
  useEffect(() => {
    const handler = () => {
      const ghostId = ghostSessionRef.current;
      if (ghostId) {
        const url = `http://${window.location.hostname}:8002/api/sessions/${encodeURIComponent(ghostId)}`;
        // fetch with keepalive survives page navigation
        fetch(url, { method: "DELETE", keepalive: true }).catch(() => {});
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  const setSessionId = useCallback(
    (id: string) => {
      // Switching away from ghost → delete it
      if (ghostSessionRef.current && ghostSessionRef.current !== id) {
        cleanupGhost();
      }
      setSessionIdRaw(id);
      setMessages([]);
      setRawMessages(null);

      apiGetSessionHistory(id)
        .then((data) => {
          if (data.messages && data.messages.length > 0) {
            const loaded: ChatMessage[] = [];
            let msgIndex = 0;
            for (const msg of data.messages) {
              if (msg.role === "user") {
                loaded.push({
                  id: `hist-user-${msgIndex++}`,
                  role: "user",
                  content: msg.content,
                  timestamp: Date.now() - (data.messages.length - msgIndex) * 1000,
                });
              } else if (msg.role === "assistant") {
                const toolCalls: ToolCall[] = (msg.tool_calls || []).map(
                  (tc: { tool: string; input?: string; output?: string }) => ({
                    tool: tc.tool,
                    input: tc.input || "",
                    output: tc.output || "",
                    status: "done" as const,
                  })
                );
                loaded.push({
                  id: `hist-asst-${msgIndex++}`,
                  role: "assistant",
                  content: msg.content,
                  toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
                  timestamp: Date.now() - (data.messages.length - msgIndex) * 1000,
                });
              }
            }
            setMessages(loaded);

            // Restore canvas: scan history for last <openclaw-canvas> content
            for (let i = loaded.length - 1; i >= 0; i--) {
              if (loaded[i].role === "assistant") {
                const canvasMatch = loaded[i].content.match(
                  /<openclaw-canvas>([\s\S]*?)<\/openclaw-canvas>/
                );
                if (canvasMatch) {
                  setCanvasCode(canvasMatch[1].trim());
                  setCanvasReady(true);
                  setCanvasStreaming(false);
                  break;
                }
              }
            }
          }
        })
        .catch(() => {});
    },
    [cleanupGhost]
  );

  const createSession = useCallback(async () => {
    // Clicking "New Chat" — delete old ghost, spawn a new one
    cleanupGhost();
    spawnGhost();
  }, [cleanupGhost, spawnGhost]);

  const renameSessionFn = useCallback(async (id: string, title: string) => {
    try {
      await apiRenameSession(id, title);
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title } : s))
      );
    } catch {
      // ignore
    }
  }, []);

  const deleteSessionFn = useCallback(
    async (id: string) => {
      try {
        await apiDeleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (sessionId === id) {
          // Deleted the active session → spawn a fresh ghost
          spawnGhost();
        }
      } catch {
        // ignore
      }
    },
    [sessionId, spawnGhost]
  );

  const loadRawMessages = useCallback(() => {
    if (!sessionId) return;
    apiGetRawMessages(sessionId)
      .then((data) => setRawMessages(data.messages))
      .catch(() => setRawMessages(null));
  }, [sessionId]);

  // ── Compression ──────────────────────────────────────

  const compressCurrentSession = useCallback(async () => {
    if (isCompressing) return;
    setIsCompressing(true);
    try {
      await apiCompressSession(sessionId);
      loadRawMessages();
      apiGetSessionHistory(sessionId)
        .then((data) => {
          if (data.messages && data.messages.length > 0) {
            const loaded: ChatMessage[] = [];
            let msgIndex = 0;
            for (const msg of data.messages) {
              if (msg.role === "user") {
                loaded.push({
                  id: `hist-user-${msgIndex++}`,
                  role: "user",
                  content: msg.content,
                  timestamp: Date.now() - (data.messages.length - msgIndex) * 1000,
                });
              } else if (msg.role === "assistant") {
                const toolCalls: ToolCall[] = (msg.tool_calls || []).map(
                  (tc: { tool: string; input?: string; output?: string }) => ({
                    tool: tc.tool,
                    input: tc.input || "",
                    output: tc.output || "",
                    status: "done" as const,
                  })
                );
                loaded.push({
                  id: `hist-asst-${msgIndex++}`,
                  role: "assistant",
                  content: msg.content,
                  toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
                  timestamp: Date.now() - (data.messages.length - msgIndex) * 1000,
                });
              }
            }
            setMessages(loaded);
          } else {
            setMessages([]);
          }
        })
        .catch(() => {});
    } catch {
      // ignore
    } finally {
      setIsCompressing(false);
    }
  }, [isCompressing, sessionId, loadRawMessages]);

  // ── RAG mode ────────────────────────────────────────

  const toggleRagMode = useCallback(() => {
    const newMode = !ragMode;
    setRagMode(newMode);
    apiSetRagMode(newMode).catch(() => setRagMode(ragMode));
  }, [ragMode]);

  // ── Title typing animation helper ─────────────────

  /** Add a session to the list with a character-by-character typing animation. */
  const materializeSession = useCallback(
    (id: string, fullTitle: string) => {
      // Clear any ongoing animation
      if (titleAnimTimerRef.current) {
        clearInterval(titleAnimTimerRef.current);
        titleAnimTimerRef.current = null;
      }

      // Ghost has materialized — it's no longer a ghost
      if (ghostSessionRef.current === id) {
        ghostSessionRef.current = null;
      }

      // Insert the session at the top with empty title, then animate
      const entry: SessionMeta = { id, title: "", updated_at: Date.now() / 1000 };
      setSessions((prev) => {
        if (prev.some((s) => s.id === id)) {
          // Already exists (shouldn't normally happen, but handle gracefully)
          return prev.map((s) => (s.id === id ? { ...s, title: "" } : s));
        }
        return [entry, ...prev];
      });

      // Animate title character by character
      let idx = 0;
      titleAnimTimerRef.current = setInterval(() => {
        idx++;
        const partial = fullTitle.slice(0, idx);
        setSessions((prev) =>
          prev.map((s) => (s.id === id ? { ...s, title: partial } : s))
        );
        if (idx >= fullTitle.length) {
          if (titleAnimTimerRef.current) {
            clearInterval(titleAnimTimerRef.current);
            titleAnimTimerRef.current = null;
          }
        }
      }, 40);
    },
    []
  );

  // Cleanup animation timer on unmount
  useEffect(() => {
    return () => {
      if (titleAnimTimerRef.current) clearInterval(titleAnimTimerRef.current);
    };
  }, []);

  // ── Send message ───────────────────────────────────

  const currentAssistantIdRef = useRef("");

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming || isCompressing) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: Date.now(),
      };

      const firstAssistantId = `assistant-${Date.now()}`;
      const assistantMsg: ChatMessage = {
        id: firstAssistantId,
        role: "assistant",
        content: "",
        toolCalls: [],
        timestamp: Date.now(),
      };

      currentAssistantIdRef.current = firstAssistantId;
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      abortRef.current = false;

      try {
        for await (const event of streamChat(text, sessionId)) {
          if (abortRef.current) break;

          if (event.event === "retrieval") {
            const targetId = currentAssistantIdRef.current;
            const retrievalData = event.data as {
              query: string;
              results: Array<{ text: string; score: string; source: string }>;
            };
            setMessages((prev) => {
              const updated = [...prev];
              const idx = updated.findIndex((m) => m.id === targetId);
              if (idx === -1) return prev;
              updated[idx] = { ...updated[idx], retrievals: retrievalData.results };
              return updated;
            });
            continue;
          }

          if (event.event === "title") {
            const titleData = event.data as { session_id: string; title: string };
            // Materialize the ghost into the sidebar with typing animation
            materializeSession(titleData.session_id, titleData.title);
            continue;
          }

          if (event.event === "canvas") {
            if (!canvasReady) {
              setCanvasCode(event.data.html as string);
              setCanvasReady(true);
              setCanvasStreaming(false);
            }
            continue;
          }

          if (event.event === "new_response") {
            const newId = `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
            currentAssistantIdRef.current = newId;
            setMessages((prev) => [
              ...prev,
              { id: newId, role: "assistant", content: "", toolCalls: [], timestamp: Date.now() },
            ]);
            continue;
          }

          const targetId = currentAssistantIdRef.current;

          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === targetId);
            if (idx === -1) return prev;
            const msg = { ...updated[idx] };

            switch (event.event) {
              case "token": {
                const tokenText = (event.data.content as string) || "";
                msg.content += tokenText;

                // ── Canvas streaming detection ──
                if (!inCanvasRef.current) {
                  const openTag = "<openclaw-canvas>";
                  if (msg.content.includes(openTag)) {
                    inCanvasRef.current = true;
                    setCanvasStreaming(true);
                    setCanvasReady(false);
                    const afterTag = msg.content.split(openTag)[1] || "";
                    const cleaned = afterTag.replace(/<\/openclaw-canvas>[\s\S]*$/, "");
                    canvasBufferRef.current = cleaned;
                    setCanvasCode(cleaned);
                  }
                } else {
                  canvasBufferRef.current += tokenText;
                  const closeTag = "</openclaw-canvas>";
                  if (canvasBufferRef.current.includes(closeTag)) {
                    const finalCode = canvasBufferRef.current.split(closeTag)[0];
                    setCanvasCode(finalCode);
                    setCanvasReady(true);
                    setCanvasStreaming(false);
                    inCanvasRef.current = false;
                  } else {
                    setCanvasCode(canvasBufferRef.current);
                  }
                }
                break;
              }

              case "tool_start":
                msg.toolCalls = [
                  ...(msg.toolCalls || []),
                  { tool: event.data.tool as string, input: event.data.input as string, status: "running" },
                ];
                break;

              case "tool_end": {
                const calls = [...(msg.toolCalls || [])];
                for (let i = calls.length - 1; i >= 0; i--) {
                  if (calls[i].tool === event.data.tool && calls[i].status === "running") {
                    calls[i] = { ...calls[i], output: event.data.output as string, status: "done" };
                    break;
                  }
                }
                msg.toolCalls = calls;
                break;
              }

              case "done":
                break;

              case "error":
                msg.content += `\n\n**Error:** ${event.data.error || "Unknown error"}`;
                break;
            }

            updated[idx] = msg;
            return updated;
          });
        }
      } catch (err) {
        const targetId = currentAssistantIdRef.current;
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((m) => m.id === targetId);
          if (idx !== -1) {
            updated[idx] = {
              ...updated[idx],
              content: updated[idx].content + `\n\n**Connection error:** ${err instanceof Error ? err.message : "Unknown"}`,
            };
          }
          return updated;
        });
      } finally {
        setIsStreaming(false);
        loadSessions();
      }
    },
    [isStreaming, isCompressing, sessionId, loadSessions, materializeSession]
  );

  return (
    <AppContext.Provider
      value={{
        messages,
        isStreaming,
        sendMessage,
        sessionId,
        setSessionId,
        sessions,
        loadSessions,
        createSession,
        renameSession: renameSessionFn,
        deleteSession: deleteSessionFn,
        sidebarOpen,
        setSidebarOpen,
        toggleSidebar,
        rawMessages,
        loadRawMessages,
        isCompressing,
        compressCurrentSession,
        ragMode,
        toggleRagMode,
        canvasCode,
        canvasReady,
        canvasStreaming,
        setCanvasCode,
        setCanvasReady,
        resetCanvas,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
