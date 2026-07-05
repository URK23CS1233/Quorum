import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { authApi, api, streamChat, createMetricsSocket } from "./api";
import { saveAuth, getAccessToken } from "./auth";

function jsonResponse(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
  };
}

function sseResponse(lines: string[]) {
  const enc = new TextEncoder();
  return {
    ok: true,
    status: 200,
    body: new ReadableStream({
      start(controller) {
        for (const l of lines) controller.enqueue(enc.encode(l));
        controller.close();
      },
    }),
  };
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  localStorage.clear();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ── authApi ─────────────────────────────────────────────────────
describe("authApi", () => {
  it("login returns tokens on success", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ access_token: "a", refresh_token: "r" }));
    const res = await authApi.login("a@b.com", "pw");
    expect(res.access_token).toBe("a");
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/auth/login");
    expect(opts.method).toBe("POST");
  });

  it("login throws the server detail on failure", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: "Invalid email or password" }, { ok: false, status: 401 }));
    await expect(authApi.login("a@b.com", "bad")).rejects.toThrow("Invalid email or password");
  });

  it("register throws on failure", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: "Email already registered" }, { ok: false, status: 409 }));
    await expect(authApi.register("N", "a@b.com", "pw", "Org"))
      .rejects.toThrow("Email already registered");
  });
});

// ── apiFetch (via api.getStatus) ────────────────────────────────
describe("apiFetch auth handling", () => {
  it("attaches the bearer token when present", async () => {
    saveAuth({ access_token: "tok-123", refresh_token: "r" });
    fetchMock.mockResolvedValueOnce(jsonResponse({ mode: "healthy" }));

    await api.getStatus();

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer tok-123");
  });

  it("refreshes and retries once on a 401", async () => {
    saveAuth({ access_token: "old", refresh_token: "refresh-1" });
    fetchMock
      .mockResolvedValueOnce(jsonResponse({}, { ok: false, status: 401 }))            // original
      .mockResolvedValueOnce(jsonResponse({ access_token: "new", refresh_token: "refresh-2" })) // refresh
      .mockResolvedValueOnce(jsonResponse({ mode: "healthy" }));                      // retry

    const result = await api.getStatus();

    expect(result).toEqual({ mode: "healthy" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    // token was rotated in storage and used on the retry
    expect(getAccessToken()).toBe("new");
    const retryOpts = fetchMock.mock.calls[2][1];
    expect(retryOpts.headers.Authorization).toBe("Bearer new");
  });

  it("clears auth when the refresh also fails", async () => {
    saveAuth({ access_token: "old", refresh_token: "refresh-1" });
    // Avoid the jsdom "navigation not implemented" noise from the redirect.
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock
      .mockResolvedValueOnce(jsonResponse({}, { ok: false, status: 401 }))   // original
      .mockResolvedValueOnce(jsonResponse({}, { ok: false, status: 401 }));  // refresh fails

    await api.getStatus().catch(() => {});

    expect(getAccessToken()).toBeNull();
    errorSpy.mockRestore();
  });
});

// ── api wrappers ────────────────────────────────────────────────
describe("api wrappers", () => {
  it("simulateIncident posts the scenario", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    await api.simulateIncident("error_storm");
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/simulate/incident");
    expect(JSON.parse(opts.body)).toEqual({ scenario: "error_storm" });
  });

  it("rollback posts the target deployment id", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    await api.rollback("dep-42");
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/rollback");
    expect(JSON.parse(opts.body).target_deployment_id).toBe("dep-42");
  });
});

// ── streamChat ──────────────────────────────────────────────────
describe("streamChat", () => {
  it("parses SSE frames into chunk and done callbacks", async () => {
    fetchMock.mockResolvedValueOnce(sseResponse([
      'data: {"text":"Roll ","conversation_id":"c1"}\n\n',
      'data: {"text":"back","conversation_id":"c1"}\n\n',
      'data: {"done":true,"conversation_id":"c1","tokens":12}\n\n',
    ]));

    const chunks: string[] = [];
    let doneConv = "";
    let doneTokens = 0;

    await streamChat("hi", null,
      (text) => chunks.push(text),
      (convId, tokens) => { doneConv = convId; doneTokens = tokens; });

    expect(chunks.join("")).toBe("Roll back");
    expect(doneConv).toBe("c1");
    expect(doneTokens).toBe(12);
  });

  it("throws when the stream response is not ok", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500, body: null });
    await expect(streamChat("hi", null, () => {}, () => {}))
      .rejects.toThrow("Chat stream failed");
  });
});

// ── createMetricsSocket ─────────────────────────────────────────
describe("createMetricsSocket", () => {
  class FakeWebSocket {
    static last: FakeWebSocket | null = null;
    url: string;
    onmessage: ((ev: { data: string }) => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: (() => void) | null = null;
    closed = false;
    constructor(url: string) {
      this.url = url;
      FakeWebSocket.last = this;
    }
    close() { this.closed = true; }
  }

  beforeEach(() => vi.stubGlobal("WebSocket", FakeWebSocket));

  it("routes metrics and incident messages to the right callbacks", () => {
    saveAuth({ access_token: "wstok", refresh_token: "r" });
    const metrics: unknown[] = [];
    const incidents: unknown[] = [];

    const close = createMetricsSocket(
      (m) => metrics.push(m),
      (a) => incidents.push(a));

    const ws = FakeWebSocket.last!;
    expect(ws.url).toContain("token=wstok");

    ws.onmessage!({ data: JSON.stringify({ type: "metrics", data: { cpu: 42 } }) });
    ws.onmessage!({ data: JSON.stringify({ type: "incident", data: { anomaly_type: "x" } }) });

    expect(metrics).toEqual([{ cpu: 42 }]);
    expect(incidents).toEqual([{ anomaly_type: "x" }]);

    close();
    expect(ws.closed).toBe(true);
  });

  it("ignores malformed messages without throwing", () => {
    const close = createMetricsSocket(() => {}, () => {});
    const ws = FakeWebSocket.last!;
    expect(() => ws.onmessage!({ data: "not json" })).not.toThrow();
    close();
  });
});
