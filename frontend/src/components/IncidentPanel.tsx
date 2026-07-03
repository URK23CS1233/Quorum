"use client";
import { useRef } from "react";
import type { QuorumAnalysis } from "@/lib/api";
import { ShieldCheck, AlertTriangle, GitCommit, CheckCircle, Loader } from "lucide-react";

interface Props {
  analysis: QuorumAnalysis | null;
  onRollback: (deploymentId: string) => void;
  isRollingBack?: boolean;
}

const confidenceStyle = {
  high:   { bg: "#10b98122", text: "#10b981", label: "HIGH" },
  medium: { bg: "#f59e0b22", text: "#f59e0b", label: "MED" },
  low:    { bg: "#ef444422", text: "#ef4444", label: "LOW" },
};

// Map graph relationship types to subtle accent colors
const relationshipColor = (rel: string): string => {
  const r = rel.toLowerCase();
  if (r.includes("caus")) return "#ef4444";
  if (r.includes("fix") || r.includes("resolv")) return "#10b981";
  if (r.includes("deploy")) return "#6366f1";
  if (r.includes("affect") || r.includes("impact")) return "#f59e0b";
  return "#6366f1";
};

export default function IncidentPanel({ analysis, onRollback, isRollingBack }: Props) {
  const rollbackBtnRef = useRef<HTMLButtonElement>(null);

  const handleRollback = () => {
    if (!analysis) return;
    // ripple is handled by btn-ripple CSS class; just call the callback
    onRollback(analysis.safe_state_deployment_id);
  };

  // ── Healthy state ────────────────────────────────────────────────────────────
  if (!analysis) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-center border border-[#1e1e2e] rounded-xl p-6 bg-[#0e0e18]">
        {/* Glow ring behind shield */}
        <div className="relative flex items-center justify-center">
          <div
            className="absolute w-20 h-20 rounded-full opacity-20 animate-pulse-glow"
            style={{ background: "radial-gradient(circle, #10b981 0%, transparent 70%)" }}
          />
          <div
            className="absolute w-14 h-14 rounded-full border border-[#10b981]/20 animate-spin"
            style={{ animationDuration: "8s" }}
          />
          <ShieldCheck size={48} className="text-[#10b981] opacity-80 relative z-10 animate-pulse-glow" />
        </div>

        <div>
          <div className="text-slate-300 font-semibold mb-1 animate-fade-up stagger-1">
            All Systems Nominal
          </div>
          <div className="text-xs text-slate-500 leading-relaxed animate-fade-up stagger-2">
            Quorum is watching your production metrics.<br />
            When an anomaly fires, the safe rollback state<br />
            will appear here instantly.
          </div>
        </div>

        {/* Try hint with blinking cursor */}
        <div className="text-xs text-slate-600 border border-[#1e1e2e] rounded-lg px-3 py-2 animate-fade-up stagger-3 flex items-center gap-1">
          Try: Simulate → Error Storm
          <span
            className="w-0.5 h-3 bg-slate-600 inline-block ml-1 animate-pulse rounded-sm"
            style={{ animationDuration: "1.1s" }}
          />
        </div>
      </div>
    );
  }

  // ── Incident state ───────────────────────────────────────────────────────────
  const conf = confidenceStyle[analysis.confidence] ?? confidenceStyle.low;
  const isUnknown = analysis.safe_state_deployment_id === "unknown";

  return (
    <div
      className={`
        h-full flex flex-col gap-3 border border-[#ef4444] rounded-xl p-4 bg-[#0e0e18]
        animate-slide-left animate-incident
        overflow-y-auto
      `}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-2">
        <AlertTriangle
          size={22}
          className="text-[#ef4444] animate-pulse-dot shrink-0"
          style={{ filter: "drop-shadow(0 0 6px rgba(239,68,68,.7))" }}
        />
        <span
          className="text-[#ef4444] font-bold text-sm uppercase tracking-wider"
          style={{ textShadow: "0 0 12px rgba(239,68,68,.6)" }}
        >
          Quorum Incident
        </span>
        <span
          className="ml-auto text-xs font-bold px-2 py-0.5 rounded-full animate-scale-spring"
          style={{ background: conf.bg, color: conf.text }}
        >
          {conf.label} CONFIDENCE
        </span>
      </div>

      {/* ── Anomaly ── */}
      <div className="rounded-lg bg-[#141422] border border-[#1e1e2e] p-3 animate-fade-up stagger-1">
        <div className="text-xs text-slate-500 mb-1 uppercase tracking-widest">Detected Anomaly</div>
        <div className="text-sm text-[#ef4444] font-mono">{analysis.anomaly_type}</div>
      </div>

      {/* ── Memory Recall ── */}
      <div className="rounded-lg bg-[#141422] border border-[#1e1e2e] p-3 flex-1 min-h-0 animate-fade-up stagger-2">
        <div className="text-xs text-slate-500 mb-2 uppercase tracking-widest flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#6366f1] animate-pulse-dot" />
          Quorum Memory Recall
        </div>
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-6">
          {analysis.recall_answer || "Recalling from Cognee memory graph…"}
        </p>
      </div>

      {/* ── Graph Insights ── */}
      {analysis.graph_insights.length > 0 && (
        <div className="rounded-lg bg-[#141422] border border-[#1e1e2e] p-3 animate-fade-up stagger-3">
          <div className="text-xs text-slate-500 mb-2 uppercase tracking-widest">Graph Insights</div>
          <div className="flex flex-col gap-1.5">
            {analysis.graph_insights.slice(0, 4).map((ins, i) => {
              const accentColor = relationshipColor(ins.relationship);
              const delay = `${i * 60}ms`;
              return (
                <div
                  key={i}
                  className="text-xs font-mono text-slate-400 flex items-center gap-1 flex-wrap pl-2 border-l-2 animate-fade-up"
                  style={{
                    borderColor: accentColor,
                    animationDelay: delay,
                    animationFillMode: "backwards",
                  }}
                >
                  <span className="text-[#6366f1]">{ins.subject}</span>
                  <span className="text-slate-600">→ {ins.relationship} →</span>
                  <span className="text-[#10b981]">{ins.object}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Safe State ── */}
      <div
        className="rounded-lg bg-[#0a1a0f] border border-[#10b981]/30 p-3 animate-fade-up stagger-4"
        style={{ boxShadow: "0 0 12px rgba(16,185,129,.08)" }}
      >
        <div className="text-xs text-[#10b981] mb-2 uppercase tracking-widest flex items-center gap-1">
          <GitCommit size={12} />
          Quorum Safe State
          <CheckCircle size={11} className="ml-auto animate-pulse-glow opacity-70" />
        </div>
        <div className="font-mono text-xs text-slate-300 space-y-0.5">
          <div>
            <span className="text-slate-500">DEP  </span>
            {analysis.safe_state_deployment_id}
          </div>
          <div>
            <span className="text-slate-500">SHA  </span>
            {analysis.safe_state_commit.slice(0, 12)}
          </div>
          <div className="text-[#10b981] truncate">{analysis.safe_state_commit_message}</div>
        </div>
      </div>

      {/* ── Rollback Button ── */}
      <button
        ref={rollbackBtnRef}
        onClick={handleRollback}
        disabled={isRollingBack || isUnknown}
        className={`
          btn-ripple
          w-full py-3 rounded-xl font-bold text-sm
          transition-all duration-200
          bg-[#10b981] text-[#07070d]
          hover:bg-[#059669] hover:shadow-[0_0_24px_rgba(16,185,129,.5)]
          active:scale-[0.97]
          disabled:opacity-40 disabled:cursor-not-allowed
          flex items-center justify-center gap-2
          animate-fade-up stagger-5
        `}
      >
        {isRollingBack ? (
          <>
            <Loader size={16} className="animate-spin" />
            Rolling back...
          </>
        ) : (
          <>
            <CheckCircle size={16} />
            Confirm Rollback
          </>
        )}
      </button>

      <p className="text-xs text-slate-600 text-center -mt-1">
        AI identifies the safe state. You confirm the action.
      </p>
    </div>
  );
}
