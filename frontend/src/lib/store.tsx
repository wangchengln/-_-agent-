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
  streamRecommend,
  buildItinerary as apiBuildItinerary,
  listSessions as apiListSessions,
  createSession as apiCreateSession,
  renameSession as apiRenameSession,
  deleteSession as apiDeleteSession,
  getRawMessages as apiGetRawMessages,
  getSessionHistory as apiGetSessionHistory,
  getSessionIrf as apiGetSessionIrf,
  compressSession as apiCompressSession,
  getRagMode as apiGetRagMode,
  setRagMode as apiSetRagMode,
} from "./api";
import type {
  FeedItem,
  PreferenceProfile,
  RecommendErrorPayload,
  RecommendFeedPayload,
  TransportMode,
  WeekendItinerary,
  ItineraryErrorPayload,
} from "./recommend-types";
import {
  buildItineraryCanvasHtml,
  buildPoiAskPrompt,
  classifyWeekendChatInput,
} from "./weekend-bridge";
import { syncTravelPreferencesToMemory } from "./travel-memory";
import {
  isRecommendErrorPayload,
  isRecommendFeedPayload,
  isBuildItineraryResponse,
  isItineraryErrorCode,
  isWeekendItinerary,
  MAX_ITINERARY_STOPS,
  MIN_ITINERARY_STOPS,
} from "./recommend-types";

const RECOMMEND_MODE_STORAGE_KEY = "openclaw-scene-mode";

function parseHistoryMessages(
  messages: Array<{
    role: string;
    content: string;
    tool_calls?: Array<{ tool: string; input?: string; output?: string }>;
  }>
): ChatMessage[] {
  const loaded: ChatMessage[] = [];
  let msgIndex = 0;
  for (const msg of messages) {
    if (msg.role === "user") {
      loaded.push({
        id: `hist-user-${msgIndex++}`,
        role: "user",
        content: msg.content,
        timestamp: Date.now() - (messages.length - msgIndex) * 1000,
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
        timestamp: Date.now() - (messages.length - msgIndex) * 1000,
      });
    }
  }
  return loaded;
}

function extractCanvasFromMessages(messages: ChatMessage[]): string | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") {
      const canvasMatch = messages[i].content.match(
        /<openclaw-canvas>([\s\S]*?)<\/openclaw-canvas>/
      );
      if (canvasMatch) {
        return canvasMatch[1].trim();
      }
    }
  }
  return null;
}

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
  has_irf?: boolean;
  irf_round?: number | null;
  irf_summary?: string | null;
}

export interface RawMessage {
  role: string;
  content: string;
  tool_calls?: Array<{ tool: string; input?: string; output?: string }>;
}

export interface ToastItem {
  id: string;
  message: string;
  tone?: "info" | "success" | "warning";
  durationMs?: number;
}

interface AppState {
  // Chat
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (text: string) => Promise<void>;
  chatDraft: string;
  chatFocusNonce: number;
  injectChatPrompt: (prompt: string, options?: { send?: boolean }) => void;
  askAboutPoi: (item: FeedItem) => void;

  // Toasts
  toasts: ToastItem[];
  pushToast: (
    message: string,
    options?: { tone?: ToastItem["tone"]; durationMs?: number }
  ) => void;
  dismissToast: (id: string) => void;

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
  itineraryCanvasToken: number;

  // Recommend / IRF
  recommendMode: boolean;
  setRecommendMode: (enabled: boolean) => void;
  toggleRecommendMode: () => void;
  currentFeed: RecommendFeedPayload | null;
  feedHistory: RecommendFeedPayload[];
  round: number;
  preference: PreferenceProfile | null;
  intentSummary: string;
  needsClarification: boolean;
  isRecommending: boolean;
  recommendToolCalls: ToolCall[];
  recommendRationale: string;
  lastRecommendError: RecommendErrorPayload | null;
  lastRecommendCommand: string;
  sendRecommendCommand: (text: string, options?: { k?: number }) => Promise<void>;
  resetRecommendState: () => void;

  // Itinerary selection (Day 6.5)
  selectedPoiIds: string[];
  transportMode: TransportMode;
  setTransportMode: (mode: TransportMode) => void;
  toggleSelectPoi: (poiId: string) => void;
  clearSelectedPois: () => void;
  isBuildingItinerary: boolean;
  currentItinerary: WeekendItinerary | null;
  lastItineraryError: ItineraryErrorPayload | null;
  buildWeekendItinerary: () => Promise<void>;
  activeItineraryStopId: string | null;
  setActiveItineraryStopId: (poiId: string | null) => void;
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
  const recommendAbortRef = useRef(false);
  const sendRecommendCommandRef = useRef<
    (text: string, options?: { k?: number }) => Promise<void>
  >(async () => {});

  const [chatDraft, setChatDraft] = useState("");
  const [chatFocusNonce, setChatFocusNonce] = useState(0);
  const [itineraryCanvasToken, setItineraryCanvasToken] = useState(0);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  // Scene: true = 周末出行 (dual layout), false = 通用助手
  const [recommendMode, setRecommendModeState] = useState(true);
  const [currentFeed, setCurrentFeed] = useState<RecommendFeedPayload | null>(null);
  const [feedHistory, setFeedHistory] = useState<RecommendFeedPayload[]>([]);
  const [round, setRound] = useState(0);
  const [preference, setPreference] = useState<PreferenceProfile | null>(null);
  const [intentSummary, setIntentSummary] = useState("");
  const [needsClarification, setNeedsClarification] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [recommendToolCalls, setRecommendToolCalls] = useState<ToolCall[]>([]);
  const [recommendRationale, setRecommendRationale] = useState("");
  const [lastRecommendError, setLastRecommendError] =
    useState<RecommendErrorPayload | null>(null);
  const [lastRecommendCommand, setLastRecommendCommand] = useState("");

  // Itinerary selection / planning
  const [selectedPoiIds, setSelectedPoiIds] = useState<string[]>([]);
  const [transportMode, setTransportMode] = useState<TransportMode>("walking");
  const [isBuildingItinerary, setIsBuildingItinerary] = useState(false);
  const [currentItinerary, setCurrentItinerary] = useState<WeekendItinerary | null>(null);
  const [lastItineraryError, setLastItineraryError] =
    useState<ItineraryErrorPayload | null>(null);
  const [activeItineraryStopId, setActiveItineraryStopId] = useState<string | null>(null);

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

  const resetRecommendState = useCallback(() => {
    setCurrentFeed(null);
    setFeedHistory([]);
    setRound(0);
    setPreference(null);
    setIntentSummary("");
    setNeedsClarification(false);
    setRecommendRationale("");
    setRecommendToolCalls([]);
    setLastRecommendError(null);
    setLastRecommendCommand("");
    recommendAbortRef.current = false;
    setSelectedPoiIds([]);
    setCurrentItinerary(null);
    setLastItineraryError(null);
    setActiveItineraryStopId(null);
  }, []);

  const applyIrfRestore = useCallback(
    (data: {
      round?: number;
      preference?: PreferenceProfile | null;
      last_command?: string | null;
      feed?: RecommendFeedPayload | null;
      itinerary?: WeekendItinerary | null;
    }) => {
      setIntentSummary("");
      setNeedsClarification(false);
      setRecommendRationale("");
      setRecommendToolCalls([]);
      setLastRecommendError(null);
      setSelectedPoiIds([]);
      setLastItineraryError(null);
      setLastRecommendCommand(data.last_command ?? "");

      if (data.feed && isRecommendFeedPayload(data.feed)) {
        setCurrentFeed(data.feed);
        setRound(data.feed.round);
        setPreference(data.feed.preference);
        setFeedHistory([data.feed]);
      } else {
        setCurrentFeed(null);
        setRound(typeof data.round === "number" ? data.round : 0);
        setFeedHistory([]);
        if (data.preference) {
          setPreference(data.preference);
        }
      }

      if (data.itinerary && isWeekendItinerary(data.itinerary)) {
        setCurrentItinerary(data.itinerary);
        setActiveItineraryStopId(data.itinerary.stops[0]?.poi_id ?? null);
        setTransportMode(data.itinerary.transport_mode);
        setCanvasCode(buildItineraryCanvasHtml(data.itinerary));
        setCanvasReady(true);
        setCanvasStreaming(false);
      } else {
        setCurrentItinerary(null);
        setActiveItineraryStopId(null);
      }
    },
    []
  );

  /** Create a new ghost session: active but invisible in sidebar. */
  const spawnGhost = useCallback(() => {
    apiCreateSession()
      .then((meta) => {
        ghostSessionRef.current = meta.id;
        setSessionIdRaw(meta.id);
        setMessages([]);
        setRawMessages(null);
        resetRecommendState();
      })
      .catch(() => {});
  }, [resetRecommendState]);

  const resetCanvas = useCallback(() => {
    setCanvasCode("");
    setCanvasReady(false);
    setCanvasStreaming(false);
    setItineraryCanvasToken(0);
    canvasBufferRef.current = "";
    inCanvasRef.current = false;
  }, []);

  const setRecommendMode = useCallback((enabled: boolean) => {
    setRecommendModeState(enabled);
    try {
      localStorage.setItem(RECOMMEND_MODE_STORAGE_KEY, String(enabled));
    } catch {
      // ignore storage errors (private mode, etc.)
    }
  }, []);

  const toggleRecommendMode = useCallback(() => {
    setRecommendMode(!recommendMode);
  }, [recommendMode, setRecommendMode]);

  // Load RAG mode on mount
  useEffect(() => {
    apiGetRagMode()
      .then((data) => setRagMode(data.rag_mode))
      .catch(() => {});
  }, []);

  // Restore scene mode from localStorage (default: 周末出行)
  useEffect(() => {
    try {
      const stored =
        localStorage.getItem(RECOMMEND_MODE_STORAGE_KEY) ??
        localStorage.getItem("openclaw-recommend-mode");
      if (stored === "false") {
        setRecommendModeState(false);
      } else if (stored === "true") {
        setRecommendModeState(true);
      }
    } catch {
      // ignore
    }
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
      resetCanvas();
      resetRecommendState();
      setChatDraft("");
      setChatFocusNonce(0);

      apiGetSessionHistory(id)
        .then((data) => {
          if (data.messages && data.messages.length > 0) {
            const loaded = parseHistoryMessages(data.messages);
            setMessages(loaded);
            const canvasCode = extractCanvasFromMessages(loaded);
            if (canvasCode) {
              setCanvasCode(canvasCode);
              setCanvasReady(true);
              setCanvasStreaming(false);
            }
          }
        })
        .catch(() => {});

      apiGetSessionIrf(id)
        .then((irf) => {
          applyIrfRestore(irf);
        })
        .catch(() => {});
    },
    [cleanupGhost, resetRecommendState, resetCanvas, applyIrfRestore]
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

  const clearSelectedPois = useCallback(() => {
    setSelectedPoiIds([]);
  }, []);

  const toggleSelectPoi = useCallback((poiId: string) => {
    setLastItineraryError(null);
    setSelectedPoiIds((prev) => {
      if (prev.includes(poiId)) {
        return prev.filter((id) => id !== poiId);
      }
      if (prev.length >= MAX_ITINERARY_STOPS) {
        return prev;
      }
      return [...prev, poiId];
    });
  }, []);

  const pushToast = useCallback(
    (
      message: string,
      options?: { tone?: ToastItem["tone"]; durationMs?: number }
    ) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      setToasts((prev) => [
        ...prev.slice(-4),
        {
          id,
          message,
          tone: options?.tone ?? "info",
          durationMs: options?.durationMs,
        },
      ]);
    },
    []
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const buildWeekendItinerary = useCallback(async () => {
    if (isBuildingItinerary || isRecommending || isCompressing) return;
    if (selectedPoiIds.length < MIN_ITINERARY_STOPS) return;

    setIsBuildingItinerary(true);
    setLastItineraryError(null);

    try {
      const response = await apiBuildItinerary({
        session_id: sessionId,
        poi_ids: selectedPoiIds,
        transport_mode: transportMode,
      });

      if (!isBuildItineraryResponse(response)) {
        throw new Error("Invalid itinerary response");
      }

      setCurrentItinerary(response.itinerary);
      setActiveItineraryStopId(
        response.itinerary.stops[0]?.poi_id ?? null
      );
      setCanvasCode(buildItineraryCanvasHtml(response.itinerary));
      setCanvasReady(true);
      setCanvasStreaming(false);
      setItineraryCanvasToken(Date.now());
      pushToast("周末行程已生成，Canvas 时间轴已就绪", { tone: "success" });
    } catch (err) {
      const code =
        err instanceof Error &&
        isItineraryErrorCode((err as Error & { code?: string }).code)
          ? (err as Error & { code: ItineraryErrorPayload["code"] }).code
          : "internal_error";
      setLastItineraryError({
        code,
        message:
          err instanceof Error ? err.message : "行程规划失败，请稍后再试",
      });
    } finally {
      setIsBuildingItinerary(false);
    }
  }, [
    isBuildingItinerary,
    isRecommending,
    isCompressing,
    selectedPoiIds,
    sessionId,
    transportMode,
    pushToast,
  ]);

  const sendMessageRef = useRef<(text: string) => Promise<void>>(async () => {});

  const injectChatPrompt = useCallback(
    (prompt: string, options?: { send?: boolean }) => {
      const trimmed = prompt.trim();
      if (!trimmed) return;
      if (options?.send) {
        void sendMessageRef.current(trimmed);
        return;
      }
      setChatDraft(trimmed);
      setChatFocusNonce((n) => n + 1);
    },
    []
  );

  const askAboutPoi = useCallback(
    (item: FeedItem) => {
      const anchorCity =
        preference?.anchor?.city ??
        currentFeed?.preference.anchor?.city ??
        null;
      const prompt = buildPoiAskPrompt(item, {
        intentSummary: intentSummary || undefined,
        anchorCity,
      });
      injectChatPrompt(prompt);
      pushToast("已填入对话，可直接发送或修改后发送", { tone: "success" });
    },
    [preference, currentFeed, intentSummary, injectChatPrompt, pushToast]
  );

  // ── Send message ───────────────────────────────────

  const currentAssistantIdRef = useRef("");

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming || isCompressing) return;

      const trimmed = text.trim();

      if (recommendMode) {
        const hasFeed = (currentFeed?.items?.length ?? 0) > 0;
        const route = classifyWeekendChatInput(trimmed, hasFeed);
        if (route === "recommend") {
          await sendRecommendCommandRef.current(trimmed);
          return;
        }
        if (route === "both") {
          void sendRecommendCommandRef.current(trimmed);
        }
      }

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
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
        for await (const event of streamChat(trimmed, sessionId)) {
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
    [
      isStreaming,
      isCompressing,
      sessionId,
      loadSessions,
      materializeSession,
      recommendMode,
      currentFeed,
      canvasReady,
    ]
  );

  sendMessageRef.current = sendMessage;

  // ── Send IRF recommend command ─────────────────────

  const serializeToolPayload = (value: unknown): string | undefined => {
    if (value == null) return undefined;
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  };

  const sendRecommendCommand = useCallback(
    async (text: string, options?: { k?: number }) => {
      if (!text.trim() || isRecommending || isCompressing) return;

      const command = text.trim();
      setLastRecommendError(null);
      setRecommendRationale("");
      setRecommendToolCalls([]);
      setLastRecommendCommand(command);
      setIsRecommending(true);
      recommendAbortRef.current = false;

      try {
        for await (const event of streamRecommend(command, sessionId, options)) {
          if (recommendAbortRef.current) break;

          switch (event.event) {
            case "intent": {
              setIntentSummary(String(event.data.intent_summary ?? ""));
              setNeedsClarification(Boolean(event.data.needs_clarification));
              break;
            }

            case "tool_start": {
              const tool = String(event.data.tool ?? "unknown");
              setRecommendToolCalls((prev) => [
                ...prev,
                {
                  tool,
                  input: serializeToolPayload(event.data.input),
                  status: "running",
                },
              ]);
              break;
            }

            case "tool_end": {
              const tool = String(event.data.tool ?? "unknown");
              setRecommendToolCalls((prev) => {
                const calls = [...prev];
                for (let i = calls.length - 1; i >= 0; i--) {
                  if (calls[i].tool === tool && calls[i].status === "running") {
                    calls[i] = {
                      ...calls[i],
                      output: serializeToolPayload(event.data.output),
                      status: "done",
                    };
                    break;
                  }
                }
                return calls;
              });
              break;
            }

            case "feed": {
              const feedPayload = event.data;
              if (isRecommendFeedPayload(feedPayload)) {
                setCurrentFeed(feedPayload);
                setRound(feedPayload.round);
                setPreference(feedPayload.preference);
                setFeedHistory((prev) => [...prev, feedPayload]);
                setSelectedPoiIds([]);
                setCurrentItinerary(null);
                setLastItineraryError(null);
                setActiveItineraryStopId(null);
                if (feedPayload.round >= 1) {
                  void syncTravelPreferencesToMemory(
                    feedPayload.preference,
                    command
                  )
                    .then((ok) => {
                      if (ok) {
                        pushToast("出行偏好已同步到 USER.md", { tone: "success" });
                      }
                    })
                    .catch(() => {});
                }
                pushToast(`推荐已更新 · 第 ${feedPayload.round} 轮`, {
                  tone: "success",
                });
              }
              break;
            }

            case "token": {
              const content = String(event.data.content ?? "");
              if (content) {
                setRecommendRationale((prev) => prev + content);
              }
              break;
            }

            case "error": {
              if (isRecommendErrorPayload(event.data)) {
                setLastRecommendError(event.data);
              } else {
                setLastRecommendError({
                  code: "internal_error",
                  message: String(event.data.message ?? "Unknown error"),
                });
              }
              break;
            }

            case "done": {
              const doneRound = event.data.round;
              if (typeof doneRound === "number") {
                setRound(doneRound);
              }
              break;
            }

            default:
              break;
          }
        }
      } catch (err) {
        setLastRecommendError({
          code: "internal_error",
          message:
            err instanceof Error ? err.message : "Connection error",
        });
      } finally {
        setIsRecommending(false);
        loadSessions();
      }
    },
    [isRecommending, isCompressing, sessionId, loadSessions, pushToast]
  );

  sendRecommendCommandRef.current = sendRecommendCommand;

  return (
    <AppContext.Provider
      value={{
        messages,
        isStreaming,
        sendMessage,
        chatDraft,
        chatFocusNonce,
        injectChatPrompt,
        askAboutPoi,
        toasts,
        pushToast,
        dismissToast,
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
        itineraryCanvasToken,
        recommendMode,
        setRecommendMode,
        toggleRecommendMode,
        currentFeed,
        feedHistory,
        round,
        preference,
        intentSummary,
        needsClarification,
        isRecommending,
        recommendToolCalls,
        recommendRationale,
        lastRecommendError,
        lastRecommendCommand,
        sendRecommendCommand,
        resetRecommendState,
        selectedPoiIds,
        transportMode,
        setTransportMode,
        toggleSelectPoi,
        clearSelectedPois,
        isBuildingItinerary,
        currentItinerary,
        lastItineraryError,
        buildWeekendItinerary,
        activeItineraryStopId,
        setActiveItineraryStopId,
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
