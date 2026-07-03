"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shield, Eye, EyeOff, CheckCircle } from "lucide-react";
import { authApi } from "@/lib/api";
import { saveAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm]       = useState({ name: "", email: "", password: "", org_name: "" });
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw]   = useState(false);
  const [mounted, setMounted] = useState(false);
  const [focused, setFocused] = useState<string | null>(null);

  useEffect(() => {
    const t = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(t);
  }, []);

  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [key]: e.target.value })),
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setError(""); setLoading(true);
    try {
      const tokens = await authApi.register(form.name, form.email, form.password, form.org_name);
      saveAuth(tokens);
      router.replace("/dashboard/monitor");
    } catch (err: any) {
      setError(err.message ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  const focusRing = (f: string) =>
    focused === f ? "border-[#6366f1] shadow-[0_0_0_3px_rgba(99,102,241,.14),0_0_18px_rgba(99,102,241,.08)]" : "";

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-16 bg-[#07070d] relative overflow-hidden">

      {/* Orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-[#6366f1]/10 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-1/3 right-1/4 w-[320px] h-[320px] bg-[#10b981]/6 rounded-full blur-[90px] animate-float-alt" />
        <div className="absolute top-2/3 left-1/5 w-[240px] h-[240px] bg-[#a855f7]/6 rounded-full blur-[70px] animate-float" style={{ animationDelay: "2.5s" }} />
      </div>

      {/* Dot grid */}
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.09) 1px, transparent 1px)",
        backgroundSize: "28px 28px",
        WebkitMaskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 20%, transparent 100%)",
        maskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 20%, transparent 100%)",
      }} />

      {/* Card */}
      <div className={`relative w-full max-w-sm transition-all duration-300 ${mounted ? "animate-scale-spring" : "opacity-0 scale-95"}`}>

        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="animate-pulse-glow w-10 h-10 rounded-xl bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center shadow-lg shadow-[#6366f1]/30">
            <Shield size={20} className="text-white" />
          </div>
          <span className="font-bold text-xl text-white tracking-tight">Quorum</span>
        </div>

        <div className="glass rounded-2xl border border-[#1e1e2e] p-8 shadow-2xl shadow-black/50">
          <h1 className="text-2xl font-bold mb-1">
            <span className="gradient-text">Create your workspace</span>
          </h1>
          <p className="text-sm text-slate-500 mb-7">You become SUPER_ADMIN instantly — no setup required</p>

          {error && (
            <div className="mb-5 px-4 py-3 rounded-xl bg-[#ef4444]/10 border border-[#ef4444]/30 text-sm text-[#ef4444] animate-slide-down"
              style={{ boxShadow: "0 0 20px rgba(239,68,68,0.15)" }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Full name */}
            <div className="animate-fade-up stagger-1">
              <label className="block text-xs text-slate-400 mb-1.5 font-medium">Full name</label>
              <input type="text" required autoFocus className={`input-base transition-all ${focusRing("name")}`}
                placeholder="Jillu" {...field("name")}
                onFocus={() => setFocused("name")} onBlur={() => setFocused(null)} />
            </div>

            {/* Email */}
            <div className="animate-fade-up stagger-2">
              <label className="block text-xs text-slate-400 mb-1.5 font-medium">Work email</label>
              <input type="email" required className={`input-base transition-all ${focusRing("email")}`}
                placeholder="you@company.com" {...field("email")}
                onFocus={() => setFocused("email")} onBlur={() => setFocused(null)} />
            </div>

            {/* Org name */}
            <div className="animate-fade-up stagger-3">
              <label className="block text-xs text-slate-400 mb-1.5 font-medium">Organization name</label>
              <input type="text" required className={`input-base transition-all ${focusRing("org_name")}`}
                placeholder="Acme Corp" {...field("org_name")}
                onFocus={() => setFocused("org_name")} onBlur={() => setFocused(null)} />
            </div>

            {/* Password */}
            <div className="animate-fade-up stagger-4">
              <label className="block text-xs text-slate-400 mb-1.5 font-medium">Password</label>
              <div className="relative">
                <input type={showPw ? "text" : "password"} required
                  className={`input-base pr-10 transition-all ${focusRing("password")}`}
                  placeholder="Min. 8 characters" {...field("password")}
                  onFocus={() => setFocused("password")} onBlur={() => setFocused(null)} />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-200 transition-all duration-200 hover:scale-110">
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Perks */}
            <div className="animate-fade-up stagger-5 flex flex-col gap-1.5 py-1">
              {["Free to use — no credit card", "No setup required", "Full SUPER_ADMIN access immediately"].map(perk => (
                <div key={perk} className="flex items-center gap-2 text-xs text-slate-500">
                  <CheckCircle size={12} className="text-[#10b981] shrink-0" />
                  {perk}
                </div>
              ))}
            </div>

            {/* Submit */}
            <div className="animate-fade-up stagger-6">
              <button type="submit" disabled={loading}
                className="btn-ripple w-full py-3 rounded-xl font-semibold text-white
                  bg-gradient-to-r from-[#6366f1] to-[#4f46e5]
                  hover:shadow-lg hover:shadow-[#6366f1]/30
                  active:scale-[0.97]
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all duration-200 flex items-center justify-center gap-2">
                {loading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Creating workspace…
                  </>
                ) : "Create workspace"}
              </button>
            </div>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-5">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-[#6366f1] hover:text-[#818cf8] font-medium transition-colors hover:underline">
            Sign in
          </Link>
        </p>
        <p className="text-center text-xs text-slate-700 mt-2">
          <Link href="/" className="hover:text-slate-400 transition-colors">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
