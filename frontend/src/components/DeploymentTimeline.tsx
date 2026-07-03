"use client";
import type { Deployment } from "@/lib/api";
import { CheckCircle, AlertTriangle, XCircle, RefreshCw, GitCommit } from "lucide-react";

const statusMeta = {
  STABLE:      { icon: CheckCircle, color: "#10b981", label: "STABLE" },
  DEGRADED:    { icon: AlertTriangle, color: "#f59e0b", label: "DEGRADED" },
  INCIDENT:    { icon: XCircle, color: "#ef4444", label: "INCIDENT" },
  ROLLED_BACK: { icon: RefreshCw, color: "#6366f1", label: "ROLLED BACK" },
};

export default function DeploymentTimeline({ deployments }: { deployments: Deployment[] }) {
  if (deployments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500">
        <GitCommit size={32} className="opacity-40" />
        <div className="text-sm">No deployments in Quorum memory yet.</div>
        <div className="text-xs text-slate-600">Seed demo data or ingest a GitHub repo.</div>
      </div>
    );
  }

  const sorted = [...deployments].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="relative pl-8">
      {/* vertical line */}
      <div className="absolute left-3 top-0 bottom-0 w-px bg-[#1e1e2e]" />

      {sorted.map((dep, i) => {
        const meta = statusMeta[dep.status] ?? statusMeta.STABLE;
        const Icon = meta.icon;

        return (
          <div key={dep.id} className="relative mb-6 last:mb-0">
            {/* dot */}
            <div
              className="absolute -left-5 w-4 h-4 rounded-full border-2 border-[#07070d] flex items-center justify-center"
              style={{ background: meta.color + "22", borderColor: meta.color }}
            >
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: meta.color }} />
            </div>

            <div className="rounded-xl border border-[#1e1e2e] bg-[#0e0e18] p-4 hover:border-[#2e2e3e] transition-colors">
              {/* top row */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon size={14} style={{ color: meta.color }} className="shrink-0" />
                  <span className="font-mono text-xs text-slate-400 truncate">{dep.commit_sha.slice(0, 10)}</span>
                </div>
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
                  style={{ background: meta.color + "22", color: meta.color }}
                >
                  {meta.label}
                </span>
              </div>

              {/* commit message */}
              <p className="text-sm text-slate-200 font-medium mb-1 line-clamp-2">{dep.commit_message}</p>

              {/* meta */}
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
                <span>{dep.author}</span>
                <span>·</span>
                <span>{new Date(dep.timestamp).toLocaleDateString()}</span>
                {dep.repo && (
                  <>
                    <span>·</span>
                    <span className="font-mono">{dep.repo}</span>
                  </>
                )}
              </div>

              {/* services */}
              <div className="flex flex-wrap gap-1 mb-2">
                {dep.services_affected.map((s) => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded-md bg-[#141422] text-slate-400 border border-[#1e1e2e]">
                    {s}
                  </span>
                ))}
              </div>

              {/* metrics at deploy */}
              <div className="flex gap-3 text-xs font-mono text-slate-500">
                <span>CPU {dep.cpu_at_deploy.toFixed(0)}%</span>
                <span>ERR {dep.error_rate_at_deploy.toFixed(2)}%</span>
                <span>P99 {dep.latency_at_deploy.toFixed(0)}ms</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
