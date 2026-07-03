"use client";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: "SUPER_ADMIN" | "ADMIN" | "OPERATOR" | "ANALYST" | "VIEWER";
  org_id: string;
  org_name?: string;
  avatar_url?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

const STORAGE_KEY = "quorum_auth";

export function saveAuth(tokens: AuthTokens) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}

export function loadAuth(): AuthTokens | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return loadAuth()?.access_token ?? null;
}

// Role hierarchy
const ROLE_LEVEL: Record<string, number> = {
  SUPER_ADMIN: 5,
  ADMIN: 4,
  OPERATOR: 3,
  ANALYST: 2,
  VIEWER: 1,
};

export function hasRole(user: AuthUser | null, minRole: string): boolean {
  if (!user) return false;
  return (ROLE_LEVEL[user.role] ?? 0) >= (ROLE_LEVEL[minRole] ?? 0);
}

export function canOperate(user: AuthUser | null)  { return hasRole(user, "OPERATOR"); }
export function canAnalyze(user: AuthUser | null)  { return hasRole(user, "ANALYST"); }
export function canAdmin(user: AuthUser | null)    { return hasRole(user, "ADMIN"); }
export function canChat(user: AuthUser | null)     { return hasRole(user, "ANALYST"); }

export function getRoleBadgeStyle(role: string): { bg: string; text: string } {
  const styles: Record<string, { bg: string; text: string }> = {
    SUPER_ADMIN: { bg: "#ef444422", text: "#ef4444" },
    ADMIN:       { bg: "#f59e0b22", text: "#f59e0b" },
    OPERATOR:    { bg: "#6366f122", text: "#6366f1" },
    ANALYST:     { bg: "#10b98122", text: "#10b981" },
    VIEWER:      { bg: "#64748b22", text: "#94a3b8" },
  };
  return styles[role] ?? styles.VIEWER;
}
