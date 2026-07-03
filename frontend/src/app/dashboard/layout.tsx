"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { authApi } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { AuthUser } from "@/lib/auth";
import { Shield } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();
  const [user, setUser]       = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) { router.replace("/auth/login"); return; }

    authApi.me()
      .then(u => setUser(u as AuthUser))
      .catch(() => { router.replace("/auth/login"); })
      .finally(() => {
        setLoading(false);
        // Small tick so the page-enter class fires after the DOM is ready
        setTimeout(() => setMounted(true), 20);
      });
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#07070d]">
        <div className="flex flex-col items-center gap-6">
          {/* Cinematic loader */}
          <div className="relative flex items-center justify-center w-20 h-20">
            {/* Outer orbiting ring */}
            <div
              className="absolute inset-0 rounded-full border-2 border-transparent animate-spin-slow"
              style={{
                borderTopColor: "#6366f1",
                borderRightColor: "#6366f1" + "40",
              }}
            />
            {/* Middle ring counter-spin */}
            <div
              className="absolute inset-2 rounded-full border border-transparent animate-spin-slow"
              style={{
                borderBottomColor: "#4f46e5",
                animationDirection: "reverse",
                animationDuration: "3s",
              }}
            />
            {/* Shield icon with glow */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center animate-pulse-glow shadow-lg shadow-[#6366f1]/30">
              <Shield size={20} className="text-white" />
            </div>
          </div>

          {/* Shimmer text */}
          <div className="flex flex-col items-center gap-1.5">
            <span
              className="text-sm font-semibold tracking-widest uppercase"
              style={{
                background: "linear-gradient(90deg, #475569 0%, #e2e8f0 40%, #6366f1 60%, #475569 100%)",
                backgroundSize: "200% auto",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                animation: "shimmer 2s linear infinite",
              }}
            >
              Loading Quorum
            </span>
            <span className="text-[11px] text-slate-600 tracking-wider">Authenticating session…</span>
          </div>
        </div>

        {/* Inline keyframe for shimmer since globals.css may not have it */}
        <style>{`
          @keyframes shimmer {
            0%   { background-position: 200% center; }
            100% { background-position: -200% center; }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#07070d]">
      <Sidebar user={user} />
      <main
        key={pathname}
        className={`flex-1 overflow-auto transition-opacity duration-300 ${mounted ? "page-enter" : "opacity-0"}`}
      >
        {children}
      </main>
    </div>
  );
}
