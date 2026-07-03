"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Shield, Activity, Clock, Network, MessageSquare,
  Database, Settings, Users, LogOut, ChevronRight, Zap,
} from "lucide-react";
import type { AuthUser } from "@/lib/auth";
import { getRoleBadgeStyle, canOperate, canAnalyze, canAdmin } from "@/lib/auth";
import { loadAuth, clearAuth } from "@/lib/auth";
import { authApi } from "@/lib/api";

interface NavItem {
  href: string;
  icon: React.ElementType;
  label: string;
  requiredRole?: string;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard/monitor",  icon: Activity,       label: "Live Monitor" },
  { href: "/dashboard/timeline", icon: Clock,          label: "Deployment Memory" },
  { href: "/dashboard/graph",    icon: Network,        label: "Knowledge Graph" },
  { href: "/dashboard/chat",     icon: MessageSquare,  label: "AI Assistant",   requiredRole: "ANALYST" },
  { href: "/dashboard/sources",  icon: Database,       label: "Data Sources",   requiredRole: "OPERATOR" },
];

const SETTINGS_ITEMS: NavItem[] = [
  { href: "/dashboard/settings",         icon: Settings, label: "Profile" },
  { href: "/dashboard/settings/users",   icon: Users,    label: "Team",    requiredRole: "ADMIN" },
];

const ROLE_LEVEL: Record<string, number> = {
  SUPER_ADMIN: 5, ADMIN: 4, OPERATOR: 3, ANALYST: 2, VIEWER: 1,
};

function hasRole(user: AuthUser | null, role: string) {
  if (!user) return false;
  return (ROLE_LEVEL[user.role] ?? 0) >= (ROLE_LEVEL[role] ?? 0);
}

// Stagger class map for nav items
const STAGGER = ["stagger-1", "stagger-2", "stagger-3", "stagger-4", "stagger-5", "stagger-6", "stagger-7", "stagger-8"] as const;

export default function Sidebar({ user }: { user: AuthUser | null }) {
  const pathname    = usePathname();
  const router      = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);
  const [mounted, setMounted]       = useState(false);

  useEffect(() => {
    // Fire mount animation after first paint
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      const auth = loadAuth();
      if (auth?.refresh_token) await authApi.logout(auth.refresh_token);
    } catch {}
    clearAuth();
    router.replace("/auth/login");
  }

  const roleStyle = getRoleBadgeStyle(user?.role ?? "VIEWER");

  // Build visible nav list so stagger indices are stable
  const visibleNavItems = NAV_ITEMS.filter(
    ({ requiredRole }) => !requiredRole || hasRole(user, requiredRole)
  );
  const visibleSettingsItems = SETTINGS_ITEMS.filter(
    ({ requiredRole }) => !requiredRole || hasRole(user, requiredRole)
  );

  return (
    <aside className="w-60 shrink-0 h-screen flex flex-col border-r border-[#1e1e2e] bg-[#0e0e18]">
      {/* Brand */}
      <div className="h-14 flex items-center gap-2.5 px-5 border-b border-[#1e1e2e]">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center shrink-0 animate-pulse-glow shadow-sm shadow-[#6366f1]/40">
          <Shield size={14} className="text-white" />
        </div>
        <span className="font-bold text-white tracking-tight">Quorum</span>
        <span className="text-[10px] text-slate-600 ml-auto">v2</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-3 overflow-y-auto">
        {/* Monitoring section */}
        <div className="mb-4">
          <p className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.12em] px-2 mb-2">
            Monitoring
          </p>
          {visibleNavItems.map(({ href, icon: Icon, label }, idx) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={[
                  "group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium mb-0.5",
                  "transition-all duration-200",
                  // Mount slide-in animation
                  mounted ? `animate-slide-right ${STAGGER[idx] ?? "stagger-1"}` : "opacity-0",
                  active
                    ? "bg-[#6366f1]/15 text-[#6366f1] border border-[#6366f1]/25 shadow-sm shadow-[#6366f1]/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#141422] border border-transparent",
                ].join(" ")}
              >
                {/* Active left-border indicator */}
                {active && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-[#6366f1] shadow-sm shadow-[#6366f1]/60"
                    aria-hidden
                  />
                )}

                <Icon
                  size={15}
                  className={[
                    "transition-all duration-200 shrink-0",
                    active
                      ? "text-[#6366f1] animate-pulse-dot"
                      : "group-hover:scale-110 group-hover:text-[#6366f1]",
                  ].join(" ")}
                />

                <span className="transition-transform duration-200 group-hover:translate-x-0.5">
                  {label}
                </span>

                {active && (
                  <ChevronRight size={12} className="ml-auto opacity-60" />
                )}
              </Link>
            );
          })}
        </div>

        {/* Settings section */}
        <div>
          <p className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.12em] px-2 mb-2">
            Settings
          </p>
          {visibleSettingsItems.map(({ href, icon: Icon, label }, idx) => {
            const active = pathname === href;
            const staggerIdx = visibleNavItems.length + idx;
            return (
              <Link
                key={href}
                href={href}
                className={[
                  "group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium mb-0.5",
                  "transition-all duration-200",
                  mounted ? `animate-slide-right ${STAGGER[staggerIdx] ?? "stagger-6"}` : "opacity-0",
                  active
                    ? "bg-[#6366f1]/15 text-[#6366f1] border border-[#6366f1]/25 shadow-sm shadow-[#6366f1]/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#141422] border border-transparent",
                ].join(" ")}
              >
                {active && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-[#6366f1] shadow-sm shadow-[#6366f1]/60"
                    aria-hidden
                  />
                )}

                <Icon
                  size={15}
                  className={[
                    "transition-all duration-200 shrink-0",
                    active
                      ? "text-[#6366f1] animate-pulse-dot"
                      : "group-hover:scale-110 group-hover:text-[#6366f1]",
                  ].join(" ")}
                />

                <span className="transition-transform duration-200 group-hover:translate-x-0.5">
                  {label}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* User card */}
      <div className="border-t border-[#1e1e2e] p-3">
        <div className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-[#141422] transition-colors duration-200">
          {/* Avatar with online ring */}
          <div className="relative shrink-0">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center text-white text-xs font-bold ring-2 ring-[#10b981]/30 animate-pulse-glow">
              {user?.name?.[0]?.toUpperCase() ?? "?"}
            </div>
            {/* Online dot */}
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#10b981] border-2 border-[#0e0e18] animate-pulse-dot" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">{user?.name ?? "…"}</div>
            <div className="flex items-center gap-1 mt-0.5">
              <span
                className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                style={{ background: roleStyle.bg, color: roleStyle.text }}
              >
                {user?.role ?? "…"}
              </span>
            </div>
          </div>

          {/* Logout — icon spins 180deg on hover */}
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="p-1.5 rounded-lg text-slate-600 hover:text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors duration-200 group/logout"
            title="Sign out"
          >
            <LogOut
              size={14}
              className="transition-transform duration-300 group-hover/logout:rotate-180"
            />
          </button>
        </div>

        {user?.org_name && (
          <div className="text-[10px] text-slate-600 px-2 mt-1 truncate flex items-center gap-1">
            <span className="w-1 h-1 rounded-full bg-[#6366f1]/40 animate-pulse-glow inline-block" />
            {user.org_name}
          </div>
        )}
      </div>
    </aside>
  );
}
