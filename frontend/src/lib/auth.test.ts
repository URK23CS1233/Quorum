import { describe, it, expect, beforeEach } from "vitest";
import {
  saveAuth, loadAuth, clearAuth, getAccessToken,
  hasRole, canOperate, canAnalyze, canAdmin, canChat,
  getRoleBadgeStyle, type AuthUser,
} from "./auth";

const TOKENS = { access_token: "access-abc", refresh_token: "refresh-xyz" };

function user(role: AuthUser["role"]): AuthUser {
  return { id: "1", email: "a@b.com", name: "A", role, org_id: "o" };
}

describe("auth token storage", () => {
  beforeEach(() => localStorage.clear());

  it("saves and loads tokens", () => {
    saveAuth(TOKENS);
    expect(loadAuth()).toEqual(TOKENS);
  });

  it("returns the access token", () => {
    saveAuth(TOKENS);
    expect(getAccessToken()).toBe("access-abc");
  });

  it("returns null when nothing stored", () => {
    expect(loadAuth()).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("clears stored auth", () => {
    saveAuth(TOKENS);
    clearAuth();
    expect(loadAuth()).toBeNull();
  });

  it("returns null on corrupt storage", () => {
    localStorage.setItem("quorum_auth", "{not valid json");
    expect(loadAuth()).toBeNull();
  });
});

describe("hasRole hierarchy", () => {
  it("grants access at or above the required level", () => {
    expect(hasRole(user("ADMIN"), "OPERATOR")).toBe(true);
    expect(hasRole(user("OPERATOR"), "OPERATOR")).toBe(true);
    expect(hasRole(user("SUPER_ADMIN"), "ADMIN")).toBe(true);
  });

  it("denies access below the required level", () => {
    expect(hasRole(user("VIEWER"), "OPERATOR")).toBe(false);
    expect(hasRole(user("ANALYST"), "ADMIN")).toBe(false);
  });

  it("denies a null user", () => {
    expect(hasRole(null, "VIEWER")).toBe(false);
  });

  it("denies an unknown role", () => {
    expect(hasRole({ ...user("VIEWER"), role: "GHOST" as never }, "VIEWER")).toBe(false);
  });
});

describe("role convenience helpers", () => {
  it("canOperate requires OPERATOR+", () => {
    expect(canOperate(user("OPERATOR"))).toBe(true);
    expect(canOperate(user("ANALYST"))).toBe(false);
  });

  it("canAnalyze / canChat require ANALYST+", () => {
    expect(canAnalyze(user("ANALYST"))).toBe(true);
    expect(canChat(user("ANALYST"))).toBe(true);
    expect(canChat(user("VIEWER"))).toBe(false);
  });

  it("canAdmin requires ADMIN+", () => {
    expect(canAdmin(user("ADMIN"))).toBe(true);
    expect(canAdmin(user("OPERATOR"))).toBe(false);
  });
});

describe("getRoleBadgeStyle", () => {
  it("returns a distinct style per known role", () => {
    expect(getRoleBadgeStyle("SUPER_ADMIN").text).toBe("#ef4444");
    expect(getRoleBadgeStyle("ANALYST").text).toBe("#10b981");
  });

  it("falls back to the VIEWER style for unknown roles", () => {
    expect(getRoleBadgeStyle("MADE_UP")).toEqual(getRoleBadgeStyle("VIEWER"));
  });
});
