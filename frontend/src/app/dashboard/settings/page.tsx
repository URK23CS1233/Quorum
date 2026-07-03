"use client";
import { useState, useEffect } from "react";
import { Settings, Key, User, Activity, DollarSign } from "lucide-react";
import { authApi, chatApi } from "@/lib/api";
import type { AuthUser } from "@/lib/api";
import { getRoleBadgeStyle } from "@/lib/auth";

export default function SettingsPage() {
  const [user, setUser]     = useState<AuthUser | null>(null);
  const [usage, setUsage]   = useState<any>(null);
  const [form, setForm]     = useState({ name: "", avatar_url: "" });
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "" });
  const [saving, setSaving] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [msg, setMsg]       = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    authApi.me().then(u => { setUser(u as AuthUser); setForm({ name: u.name, avatar_url: "" }); });
    chatApi.getUsage().then(setUsage).catch(() => {});
  }, []);

  const flash = (text: string, ok: boolean) => { setMsg({ text, ok }); setTimeout(() => setMsg(null), 3000); };

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault(); setSaving(true);
    try { await authApi.updateProfile({ name: form.name }); flash("Profile updated ✓", true); }
    catch { flash("Failed to update", false); }
    finally { setSaving(false); }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault(); setPwSaving(true);
    try { await authApi.changePassword(pwForm.current_password, pwForm.new_password); flash("Password changed ✓", true); setPwForm({ current_password: "", new_password: "" }); }
    catch (err: any) { flash(err.message ?? "Failed", false); }
    finally { setPwSaving(false); }
  }

  const badge = getRoleBadgeStyle(user?.role ?? "VIEWER");

  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <Settings size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">Profile & Settings</span>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-xl mx-auto flex flex-col gap-6">

          {msg && (
            <div className={`px-4 py-3 rounded-xl text-sm border ${msg.ok ? "bg-[#10b981]/10 border-[#10b981]/30 text-[#10b981]" : "bg-[#ef4444]/10 border-[#ef4444]/30 text-[#ef4444]"}`}>
              {msg.text}
            </div>
          )}

          {/* Profile card */}
          <div className="rounded-xl border border-[#1e1e2e] bg-[#0e0e18] p-5">
            <div className="flex items-center gap-3 mb-5">
              <User size={15} className="text-[#6366f1]" />
              <span className="font-semibold text-white">Profile</span>
            </div>
            <div className="flex items-center gap-4 mb-5 p-4 rounded-xl bg-[#141422]">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center text-white text-lg font-bold">
                {user?.name?.[0]?.toUpperCase() ?? "?"}
              </div>
              <div>
                <div className="font-semibold text-white">{user?.name}</div>
                <div className="text-sm text-slate-500">{user?.email}</div>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full mt-1 inline-block" style={{ background: badge.bg, color: badge.text }}>
                  {user?.role}
                </span>
              </div>
              {user?.org_name && <div className="ml-auto text-xs text-slate-600">Org: {user.org_name}</div>}
            </div>
            <form onSubmit={saveProfile} className="flex flex-col gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Display name</label>
                <input className="input-base" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
              </div>
              <button type="submit" disabled={saving} className="self-start px-5 py-2 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] text-white text-sm font-semibold transition-colors disabled:opacity-50">
                {saving ? "Saving…" : "Save changes"}
              </button>
            </form>
          </div>

          {/* Change password */}
          <div className="rounded-xl border border-[#1e1e2e] bg-[#0e0e18] p-5">
            <div className="flex items-center gap-3 mb-4">
              <Key size={15} className="text-[#f59e0b]" />
              <span className="font-semibold text-white">Change Password</span>
            </div>
            <form onSubmit={changePassword} className="flex flex-col gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Current password</label>
                <input type="password" required className="input-base" value={pwForm.current_password} onChange={e => setPwForm(f => ({...f, current_password: e.target.value}))} />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">New password</label>
                <input type="password" required minLength={8} className="input-base" placeholder="Min. 8 characters" value={pwForm.new_password} onChange={e => setPwForm(f => ({...f, new_password: e.target.value}))} />
              </div>
              <button type="submit" disabled={pwSaving} className="self-start px-5 py-2 rounded-xl bg-[#f59e0b] hover:bg-[#d97706] text-[#07070d] text-sm font-semibold transition-colors disabled:opacity-50">
                {pwSaving ? "Changing…" : "Change password"}
              </button>
            </form>
          </div>

          {/* Token usage */}
          {usage && (
            <div className="rounded-xl border border-[#1e1e2e] bg-[#0e0e18] p-5">
              <div className="flex items-center gap-3 mb-4">
                <Activity size={15} className="text-[#10b981]" />
                <span className="font-semibold text-white">Your AI Usage</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Total tokens", value: usage.total_tokens?.toLocaleString() },
                  { label: "AI messages", value: usage.ai_messages },
                  { label: "Avg tokens/reply", value: usage.avg_tokens_per_msg },
                  { label: "Est. cost", value: `$${usage.estimated_cost_usd}` },
                ].map(({ label, value }) => (
                  <div key={label} className="p-3 rounded-xl bg-[#141422]">
                    <div className="text-xs text-slate-500 mb-1">{label}</div>
                    <div className="text-lg font-bold text-white font-mono">{value ?? "—"}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
