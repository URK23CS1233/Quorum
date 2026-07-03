"use client";
import { useState, useEffect } from "react";
import { Plus, Trash2, RefreshCw, CheckCircle, AlertCircle, Github, Database, Zap } from "lucide-react";
import { sourcesApi } from "@/lib/api";

interface Source { id: string; name: string; source_type: string; is_active: boolean; sync_count: number; last_sync: string | null; config_preview: Record<string, string>; }

const SOURCE_ICONS: Record<string, React.ElementType> = {
  github: Github, pagerduty: Zap, datadog: Database, slack: Database, manual: Database,
};

const SOURCE_COLORS: Record<string, string> = {
  github: "#10b981", pagerduty: "#ef4444", datadog: "#6366f1", slack: "#f59e0b", manual: "#64748b",
};

const SOURCE_FIELDS: Record<string, Array<{ key: string; label: string; placeholder: string; sensitive?: boolean }>> = {
  github:     [{ key: "owner", label: "Owner", placeholder: "topoteretes" }, { key: "repo", label: "Repo", placeholder: "cognee" }, { key: "token", label: "Token (optional)", placeholder: "ghp_...", sensitive: true }],
  pagerduty:  [{ key: "api_key", label: "API Key", placeholder: "u+xxxx", sensitive: true }],
  datadog:    [{ key: "api_key", label: "API Key", placeholder: "xxxx", sensitive: true }, { key: "app_key", label: "App Key", placeholder: "xxxx", sensitive: true }],
  slack:      [{ key: "webhook_url", label: "Webhook URL", placeholder: "https://hooks.slack.com/…", sensitive: true }],
  manual:     [],
};

function AddSourceModal({ onClose, onAdd }: { onClose: () => void; onAdd: () => void }) {
  const [step, setStep] = useState<"type" | "config">("type");
  const [type, setType] = useState("");
  const [name, setName] = useState("");
  const [config, setConfig] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const fields = SOURCE_FIELDS[type] ?? [];

  async function save() {
    setSaving(true); setError("");
    try {
      await sourcesApi.create({ name: name || type, source_type: type, config });
      onAdd(); onClose();
    } catch (e: any) { setError(e.message ?? "Failed"); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[#1e1e2e] bg-[#0e0e18] shadow-2xl p-6">
        <h2 className="font-bold text-white text-lg mb-4">Add Data Source</h2>

        {step === "type" && (
          <>
            <div className="grid grid-cols-2 gap-3 mb-6">
              {Object.keys(SOURCE_FIELDS).map(t => {
                const Icon = SOURCE_ICONS[t] ?? Database;
                const color = SOURCE_COLORS[t];
                return (
                  <button key={t} onClick={() => { setType(t); setStep("config"); }}
                    className={`p-4 rounded-xl border transition-all text-left ${type === t ? "border-[#6366f1]" : "border-[#1e1e2e] hover:border-[#2e2e3e]"}`}>
                    <Icon size={18} style={{ color }} className="mb-2" />
                    <div className="text-sm font-semibold text-white capitalize">{t}</div>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {step === "config" && (
          <>
            <div className="mb-4">
              <label className="block text-xs text-slate-400 mb-1.5">Source name</label>
              <input className="input-base" placeholder={`My ${type} source`} value={name} onChange={e => setName(e.target.value)} />
            </div>
            {fields.map(f => (
              <div key={f.key} className="mb-3">
                <label className="block text-xs text-slate-400 mb-1.5">{f.label}</label>
                <input className="input-base" type={f.sensitive ? "password" : "text"} placeholder={f.placeholder}
                  value={config[f.key] ?? ""}
                  onChange={e => setConfig(c => ({ ...c, [f.key]: e.target.value }))} />
              </div>
            ))}
            {fields.length === 0 && <p className="text-sm text-slate-500 mb-4">No configuration needed for manual ingestion.</p>}
            {error && <div className="text-xs text-[#ef4444] mb-3">{error}</div>}
          </>
        )}

        <div className="flex gap-2 mt-2">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-[#1e1e2e] text-slate-400 text-sm hover:border-[#2e2e3e] transition-colors">Cancel</button>
          {step === "config" && (
            <button onClick={save} disabled={saving}
              className="flex-1 py-2.5 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] text-white text-sm font-semibold transition-colors disabled:opacity-50">
              {saving ? "Adding…" : "Add Source"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SourcesManager() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const load = () => sourcesApi.list().then(setSources).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const sync = async (id: string) => {
    setSyncing(id);
    try { await sourcesApi.sync(id); await load(); }
    catch {}
    finally { setSyncing(null); }
  };

  const remove = async (id: string) => {
    if (!confirm("Remove this source?")) return;
    await sourcesApi.remove(id); load();
  };

  const toggle = async (s: Source) => {
    await sourcesApi.update(s.id, { is_active: !s.is_active }); load();
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-white">Data Sources</h2>
          <p className="text-sm text-slate-500">All connected sources feed into Cognee memory</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5] text-white text-sm font-semibold transition-colors">
          <Plus size={14} /> Add Source
        </button>
      </div>

      {loading && <div className="text-slate-500 text-sm">Loading sources…</div>}

      {!loading && sources.length === 0 && (
        <div className="text-center py-16 border border-dashed border-[#1e1e2e] rounded-2xl">
          <Database size={32} className="text-slate-600 mx-auto mb-3" />
          <div className="text-slate-400 font-medium mb-1">No sources connected</div>
          <div className="text-slate-600 text-sm mb-4">Connect GitHub, PagerDuty, Datadog or more</div>
          <button onClick={() => setShowAdd(true)}
            className="px-4 py-2 rounded-xl bg-[#6366f1] text-white text-sm font-semibold hover:bg-[#4f46e5] transition-colors">
            Add your first source
          </button>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {sources.map(s => {
          const Icon  = SOURCE_ICONS[s.source_type] ?? Database;
          const color = SOURCE_COLORS[s.source_type] ?? "#64748b";
          return (
            <div key={s.id} className="flex items-center gap-4 p-4 rounded-xl border border-[#1e1e2e] bg-[#0e0e18] hover:border-[#2e2e3e] transition-colors">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: color + "18" }}>
                <Icon size={18} style={{ color }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-white text-sm">{s.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-slate-500 capitalize">{s.source_type}</span>
                  {s.last_sync && <span className="text-xs text-slate-600">· synced {new Date(s.last_sync).toLocaleDateString()}</span>}
                  {s.sync_count > 0 && <span className="text-xs text-slate-600">· {s.sync_count} items</span>}
                </div>
              </div>

              <div className="flex items-center gap-1">
                {s.is_active
                  ? <span className="flex items-center gap-1 text-xs text-[#10b981]"><CheckCircle size={12} /> Active</span>
                  : <span className="flex items-center gap-1 text-xs text-slate-500"><AlertCircle size={12} /> Paused</span>}
              </div>

              <div className="flex items-center gap-1">
                <button onClick={() => sync(s.id)} disabled={syncing === s.id}
                  className="p-2 rounded-lg text-slate-500 hover:text-[#10b981] hover:bg-[#10b981]/10 transition-colors" title="Sync now">
                  <RefreshCw size={13} className={syncing === s.id ? "animate-spin" : ""} />
                </button>
                <button onClick={() => toggle(s)}
                  className="p-2 rounded-lg text-slate-500 hover:text-[#f59e0b] hover:bg-[#f59e0b]/10 transition-colors" title={s.is_active ? "Pause" : "Resume"}>
                  {s.is_active ? <AlertCircle size={13} /> : <CheckCircle size={13} />}
                </button>
                <button onClick={() => remove(s.id)}
                  className="p-2 rounded-lg text-slate-500 hover:text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors" title="Remove">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {showAdd && <AddSourceModal onClose={() => setShowAdd(false)} onAdd={load} />}
    </div>
  );
}
