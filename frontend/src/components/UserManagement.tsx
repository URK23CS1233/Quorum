"use client";
import { useState, useEffect } from "react";
import { Plus, Trash2, Edit2, CheckCircle, XCircle, Shield } from "lucide-react";
import { usersApi } from "@/lib/api";
import { getRoleBadgeStyle } from "@/lib/auth";

interface UserRow { id: string; name: string; email: string; role: string; is_active: boolean; last_active: string | null; created_at: string; }

const ROLES = ["SUPER_ADMIN", "ADMIN", "OPERATOR", "ANALYST", "VIEWER"] as const;

function InviteModal({ onClose, onAdd }: { onClose: () => void; onAdd: () => void }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "VIEWER" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError("");
    try { await usersApi.invite(form); onAdd(); onClose(); }
    catch (e: any) { setError(e.message ?? "Failed"); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-[#1e1e2e] bg-[#0e0e18] shadow-2xl p-6">
        <h2 className="font-bold text-white text-lg mb-4">Invite Team Member</h2>
        {error && <div className="mb-3 text-xs text-[#ef4444] px-3 py-2 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20">{error}</div>}
        <form onSubmit={save} className="flex flex-col gap-3">
          <div><label className="block text-xs text-slate-400 mb-1.5">Name</label><input required className="input-base" placeholder="Jane Smith" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} /></div>
          <div><label className="block text-xs text-slate-400 mb-1.5">Email</label><input required type="email" className="input-base" placeholder="jane@company.com" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} /></div>
          <div><label className="block text-xs text-slate-400 mb-1.5">Temporary password</label><input required type="password" className="input-base" placeholder="Min. 8 chars" value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))} /></div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Role</label>
            <select className="input-base" value={form.role} onChange={e => setForm(f => ({...f, role: e.target.value}))}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex gap-2 mt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-[#1e1e2e] text-slate-400 text-sm hover:border-[#2e2e3e] transition-colors">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] text-white text-sm font-semibold transition-colors disabled:opacity-50">{saving ? "Inviting…" : "Invite"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function UserManagement() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editRole, setEditRole] = useState("");

  const load = () => usersApi.list().then(setUsers).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const startEdit = (u: UserRow) => { setEditingId(u.id); setEditRole(u.role); };

  const saveRole = async (id: string) => {
    await usersApi.update(id, { role: editRole });
    setEditingId(null); load();
  };

  const toggleActive = async (u: UserRow) => {
    await usersApi.update(u.id, { is_active: !u.is_active }); load();
  };

  const remove = async (id: string) => {
    if (!confirm("Deactivate this user?")) return;
    await usersApi.remove(id); load();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-white">Team Members</h2>
          <p className="text-sm text-slate-500">Manage roles and access for your organization</p>
        </div>
        <button onClick={() => setShowInvite(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] text-white text-sm font-semibold transition-colors">
          <Plus size={14} /> Invite Member
        </button>
      </div>

      {loading && <div className="text-slate-500 text-sm">Loading team…</div>}

      <div className="rounded-xl border border-[#1e1e2e] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e1e2e] bg-[#0e0e18]">
              <th className="text-left px-4 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Member</th>
              <th className="text-left px-4 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Role</th>
              <th className="text-left px-4 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Status</th>
              <th className="text-left px-4 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Last active</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {users.map(u => {
              const badge = getRoleBadgeStyle(u.role);
              return (
                <tr key={u.id} className="border-b border-[#1e1e2e] last:border-0 hover:bg-[#0e0e18]/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center text-white text-xs font-bold shrink-0">
                        {u.name?.[0]?.toUpperCase() ?? "?"}
                      </div>
                      <div>
                        <div className="font-medium text-white">{u.name}</div>
                        <div className="text-xs text-slate-500">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {editingId === u.id ? (
                      <div className="flex items-center gap-1">
                        <select value={editRole} onChange={e => setEditRole(e.target.value)}
                          className="text-xs bg-[#141422] border border-[#1e1e2e] rounded-lg px-2 py-1 text-white outline-none focus:border-[#6366f1]">
                          {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                        <button onClick={() => saveRole(u.id)} className="p-1 text-[#10b981] hover:bg-[#10b981]/10 rounded transition-colors"><CheckCircle size={13} /></button>
                        <button onClick={() => setEditingId(null)} className="p-1 text-slate-500 hover:bg-[#141422] rounded transition-colors"><XCircle size={13} /></button>
                      </div>
                    ) : (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: badge.bg, color: badge.text }}>{u.role}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`flex items-center gap-1 text-xs font-medium ${u.is_active ? "text-[#10b981]" : "text-slate-500"}`}>
                      {u.is_active ? <CheckCircle size={11} /> : <XCircle size={11} />}
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {u.last_active ? new Date(u.last_active).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => startEdit(u)} className="p-1.5 rounded-lg text-slate-500 hover:text-[#6366f1] hover:bg-[#6366f1]/10 transition-colors" title="Edit role"><Edit2 size={12} /></button>
                      <button onClick={() => toggleActive(u)} className="p-1.5 rounded-lg text-slate-500 hover:text-[#f59e0b] hover:bg-[#f59e0b]/10 transition-colors" title={u.is_active ? "Deactivate" : "Reactivate"}><Shield size={12} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && users.length === 0 && (
          <div className="text-center py-10 text-slate-500 text-sm">No team members yet</div>
        )}
      </div>

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} onAdd={load} />}
    </div>
  );
}
