import { getAccessToken, saveAuth, clearAuth, loadAuth } from "./auth";

export interface Metrics {
  timestamp: string;
  cpu: number;
  error_rate: number;
  latency_p99: number;
  requests_per_second: number;
  memory_usage: number;
  status: "healthy" | "degraded" | "critical";
}

export interface QuorumAnalysis {
  triggered_at: string;
  anomaly_type: string;
  current_metrics: Record<string, number>;
  recall_answer: string;
  similar_incident_summary: string;
  safe_state_deployment_id: string;
  safe_state_commit: string;
  safe_state_commit_message: string;
  confidence: "high" | "medium" | "low";
  graph_insights: Array<{ subject: string; relationship: string; object: string }>;
}

export interface Deployment {
  id: string;
  timestamp: string;
  commit_sha: string;
  commit_message: string;
  author: string;
  services_affected: string[];
  cpu_at_deploy: number;
  error_rate_at_deploy: number;
  latency_at_deploy: number;
  status: "STABLE" | "DEGRADED" | "INCIDENT" | "ROLLED_BACK";
  branch: string;
  repo: string;
}

export interface AuthUser {
  id: string; email: string; name: string;
  role: string; org_id: string; org_name?: string;
}

const BASE = "";

async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  // Auto-refresh if 401
  if (res.status === 401) {
    const auth = loadAuth();
    if (auth?.refresh_token) {
      try {
        const rr = await fetch(`${BASE}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: auth.refresh_token }),
        });
        if (rr.ok) {
          const newTokens = await rr.json();
          saveAuth(newTokens);
          headers["Authorization"] = `Bearer ${newTokens.access_token}`;
          return fetch(`${BASE}${path}`, { ...opts, headers });
        }
      } catch {}
    }
    clearAuth();
    if (typeof window !== "undefined") window.location.href = "/auth/login";
  }
  return res;
}

export const authApi = {
  async register(name: string, email: string, password: string, org_name: string) {
    const r = await fetch(`${BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, org_name }),
    });
    if (!r.ok) throw new Error((await r.json()).detail ?? "Registration failed");
    return r.json();
  },
  async login(email: string, password: string) {
    const r = await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) throw new Error((await r.json()).detail ?? "Login failed");
    return r.json();
  },
  async me(): Promise<AuthUser> {
    const r = await apiFetch("/api/auth/me");
    if (!r.ok) throw new Error("Not authenticated");
    return r.json();
  },
  async logout(refresh_token: string) {
    await apiFetch("/api/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    });
    clearAuth();
  },
  async updateProfile(data: { name?: string; avatar_url?: string }) {
    const r = await apiFetch("/api/auth/me", { method: "PUT", body: JSON.stringify(data) });
    return r.json();
  },
  async changePassword(current_password: string, new_password: string) {
    const r = await apiFetch("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    });
    if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
    return r.json();
  },
};

export const api = {
  async getStatus() {
    const r = await apiFetch("/api/monitor/status"); return r.json();
  },
  async getIncident() {
    const r = await apiFetch("/api/monitor/incident"); return r.json();
  },
  async getDeployments(): Promise<{ deployments: Deployment[] }> {
    const r = await apiFetch("/api/monitor/deployments"); return r.json();
  },
  async getGraph() {
    const r = await apiFetch("/api/graph"); return r.json();
  },
  async simulateIncident(scenario: string) {
    const r = await apiFetch("/api/simulate/incident", {
      method: "POST", body: JSON.stringify({ scenario }),
    }); return r.json();
  },
  async resolveIncident() {
    const r = await apiFetch("/api/simulate/resolve", { method: "POST" }); return r.json();
  },
  async rollback(deployment_id: string) {
    const r = await apiFetch("/api/rollback", {
      method: "POST",
      body: JSON.stringify({ target_deployment_id: deployment_id, reason: "Human-confirmed Quorum rollback" }),
    }); return r.json();
  },
  async improveMemory() {
    const r = await apiFetch("/api/memory/improve", { method: "POST" }); return r.json();
  },
  async ingestGitHub(owner: string, repo: string) {
    const r = await apiFetch(`/api/memory/github/${owner}/${repo}`, { method: "POST" }); return r.json();
  },
};

export const usersApi = {
  async list() {
    const r = await apiFetch("/api/users/"); return r.json();
  },
  async invite(data: { name: string; email: string; password: string; role: string }) {
    const r = await apiFetch("/api/users/invite", { method: "POST", body: JSON.stringify(data) });
    if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
    return r.json();
  },
  async update(userId: string, data: { name?: string; role?: string; is_active?: boolean }) {
    const r = await apiFetch(`/api/users/${userId}`, { method: "PATCH", body: JSON.stringify(data) });
    return r.json();
  },
  async remove(userId: string) {
    const r = await apiFetch(`/api/users/${userId}`, { method: "DELETE" }); return r.json();
  },
  async auditLog() {
    const r = await apiFetch("/api/users/audit-log"); return r.json();
  },
};

export const sourcesApi = {
  async list() {
    const r = await apiFetch("/api/sources/"); return r.json();
  },
  async create(data: { name: string; source_type: string; config: Record<string, string> }) {
    const r = await apiFetch("/api/sources/", { method: "POST", body: JSON.stringify(data) });
    if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
    return r.json();
  },
  async update(id: string, data: object) {
    const r = await apiFetch(`/api/sources/${id}`, { method: "PATCH", body: JSON.stringify(data) });
    return r.json();
  },
  async remove(id: string) {
    const r = await apiFetch(`/api/sources/${id}`, { method: "DELETE" }); return r.json();
  },
  async sync(id: string) {
    const r = await apiFetch(`/api/sources/${id}/sync`, { method: "POST" }); return r.json();
  },
};

export const chatApi = {
  async getConversations() {
    const r = await apiFetch("/api/chat/conversations"); return r.json();
  },
  async getMessages(conversationId: string) {
    const r = await apiFetch(`/api/chat/conversations/${conversationId}/messages`); return r.json();
  },
  async deleteConversation(conversationId: string) {
    const r = await apiFetch(`/api/chat/conversations/${conversationId}`, { method: "DELETE" });
    return r.json();
  },
  async getUsage() {
    const r = await apiFetch("/api/chat/usage"); return r.json();
  },
  streamMessage(message: string, conversationId?: string): EventSource {
    const token = getAccessToken();
    // Use fetch-based SSE since EventSource doesn't support headers
    // We use a POST then return a readable stream
    return { message, conversationId, token } as any;
  },
};

export async function streamChat(
  message: string,
  conversationId: string | null,
  onChunk: (text: string, convId: string) => void,
  onDone: (convId: string, tokens: number) => void,
) {
  const token = getAccessToken();
  const res = await fetch(`${BASE}/api/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!res.ok || !res.body) throw new Error("Chat stream failed");

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const obj = JSON.parse(raw);
        if (obj.text)    onChunk(obj.text, obj.conversation_id ?? "");
        if (obj.done)    onDone(obj.conversation_id ?? "", obj.tokens ?? 0);
      } catch {}
    }
  }
}

export function createMetricsSocket(
  onMetrics: (m: Metrics) => void,
  onIncident: (a: QuorumAnalysis | null) => void,
): () => void {
  const token = getAccessToken();
  const wsUrl = `ws://localhost:8000/ws/metrics${token ? `?token=${token}` : ""}`;
  let ws: WebSocket;
  let reconnectTimer: ReturnType<typeof setTimeout>;
  let alive = true;

  function connect() {
    ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "metrics")  onMetrics(msg.data);
        if (msg.type === "incident") onIncident(msg.data);
      } catch {}
    };
    ws.onclose = () => { if (alive) reconnectTimer = setTimeout(connect, 2000); };
    ws.onerror = () => ws.close();
  }
  connect();
  return () => { alive = false; clearTimeout(reconnectTimer); ws?.close(); };
}
