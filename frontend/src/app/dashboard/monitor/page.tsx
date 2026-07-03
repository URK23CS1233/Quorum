"use client";
import { useEffect, useState, useRef } from "react";
import { Zap, RefreshCw, Github, ChevronDown, CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import { api, createMetricsSocket } from "@/lib/api";
import type { Metrics, QuorumAnalysis } from "@/lib/api";
import MetricsDashboard from "@/components/MetricsDashboard";
import IncidentPanel from "@/components/IncidentPanel";

const SCENARIOS = [
  { id: "error_storm",    label: "Error Storm",    desc: "Error rate → 18%" },
  { id: "cpu_spike",      label: "CPU Spike",       desc: "CPU → 96%" },
  { id: "latency_blowup", label: "Latency Blowup",  desc: "P99 → 4200ms" },
  { id: "memory_leak",    label: "Memory Leak",     desc: "Memory grows" },
];

type FlashType = "ok" | "warn" | "err";
type StatusType = "HEALTHY" | "DEGRADED" | "INCIDENT" | "CRITICAL";

const FLASH_META: Record<FlashType, { color: string; bg: string; border: string; Icon: React.ElementType; label: string }> = {
  ok:   { color: "#10b981", bg: "#10b98112", border: "#10b98140", Icon: CheckCircle,    label: "Success" },
  warn: { color: "#f59e0b", bg: "#f59e0b12", border: "#f59e0b40", Icon: AlertTriangle,  label: "Warning" },
  err:  { color: "#ef4444", bg: "#ef444412", border: "#ef444440", Icon: XCircle,        label: "Error"   },
};

export default function MonitorPage() {
  const [metrics, setMetrics]   = useState<Metrics | null>(null);
  const [history, setHistory]   = useState<Metrics[]>([]);
  const [incident, setIncident] = useState<QuorumAnalysis | null>(null);
  const [flash, setFlash]       = useState<{ msg: string; type: FlashType } | null>(null);
  const [simOpen, setSimOpen]   = useState(false);
  const [ghOpen, setGhOpen]     = useState(false);
  const [ghOwner, setGhOwner]   = useState("topoteretes");
  const [ghRepo, setGhRepo]     = useState("cognee");
  const [rollingBack, setRollingBack]   = useState(false);
  const [simSpring, setSimSpring]       = useState(false);
  const [improveSpinning, setImproveSpinning] = useState(false);
  const flashRef = useRef<ReturnType<typeof setTimeout>>();

  const showFlash = (msg: string, type: FlashType) => {
    clearTimeout(flashRef.current);
    setFlash(null);
    // Tiny tick so the enter animation re-fires each time
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setFlash({ msg, type });
        flashRef.current = setTimeout(() => setFlash(null), 4000);
      });
    });
  };

  useEffect(() => {
    return createMetricsSocket(
      m => { setMetrics(m); setHistory(h => [...h.slice(-60), m]); },
      a => setIncident(a),
    );
  }, []);

  const sysStatus: StatusType = incident ? "INCIDENT"
    : metrics?.status === "critical" ? "CRITICAL"
    : metrics?.status === "degraded" ? "DEGRADED" : "HEALTHY";

  const statusColor =
    sysStatus === "INCIDENT" || sysStatus === "CRITICAL" ? "#ef4444"
    : sysStatus === "DEGRADED" ? "#f59e0b"
    : "#10b981";

  const isUnhealthy = sysStatus !== "HEALTHY";

  async function handleSimulate(scenarioId: string, label: string) {
    setSimOpen(false);
    // Spring animation on the simulate button
    setSimSpring(true);
    setTimeout(() => setSimSpring(false), 500);
    await api.simulateIncident(scenarioId);
    showFlash(`⚡ ${label} triggered`, "warn");
  }

  async function handleImprove() {
    setImproveSpinning(true);
    try {
      await api.improveMemory();
      showFlash("Memory strengthened ✓", "ok");
    } catch {
      showFlash("Improve failed", "err");
    } finally {
      setTimeout(() => setImproveSpinning(false), 1000);
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-3 shrink-0">
        {/* Status pill */}
        <div
          className={[
            "flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border transition-all duration-300",
            isUnhealthy
              ? "animate-pulse-red ring-2 shadow-sm"
              : "shadow-none",
          ].join(" ")}
          style={{
            background:   statusColor + "18",
            borderColor:  statusColor + "40",
            color:        statusColor,
            ...(isUnhealthy ? { "--tw-ring-color": statusColor + "30" } as React.CSSProperties : {}),
          }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${isUnhealthy ? "animate-pulse-dot" : ""}`}
            style={{ background: statusColor }}
          />
          {sysStatus}
        </div>

        <div className="flex-1" />

        {/* GitHub ingest */}
        <div className="relative">
          <button
            onClick={() => { setGhOpen(o => !o); setSimOpen(false); }}
            className="btn-ripple flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#0e0e18] hover:border-[#6366f1]/30 text-slate-400 transition-all duration-150 hover:scale-[1.02] active:scale-[0.97]"
          >
            <Github size={12} /> Ingest Repo <ChevronDown size={11} className={`transition-transform duration-200 ${ghOpen ? "rotate-180" : ""}`} />
          </button>

          {ghOpen && (
            <div className="absolute right-0 top-9 z-50 w-56 rounded-xl border border-[#1e1e2e] glass shadow-xl p-3 flex flex-col gap-2 animate-slide-up">
              <input
                className="input-base text-xs py-1.5"
                placeholder="owner"
                value={ghOwner}
                onChange={e => setGhOwner(e.target.value)}
              />
              <input
                className="input-base text-xs py-1.5"
                placeholder="repo"
                value={ghRepo}
                onChange={e => setGhRepo(e.target.value)}
              />
              <button
                onClick={async () => {
                  setGhOpen(false);
                  showFlash(`Ingesting ${ghOwner}/${ghRepo}…`, "warn");
                  try {
                    const r = await api.ingestGitHub(ghOwner, ghRepo);
                    showFlash(`✓ Ingested ${r.ingested} commits`, "ok");
                  } catch {
                    showFlash("Ingest failed", "err");
                  }
                }}
                className="btn-ripple w-full py-1.5 rounded-lg bg-[#6366f1] text-white text-xs font-bold hover:bg-[#4f46e5] transition-colors hover:scale-[1.02] active:scale-[0.97]"
              >
                Ingest
              </button>
            </div>
          )}
        </div>

        {/* Improve memory */}
        <button
          onClick={handleImprove}
          className="btn-ripple flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#0e0e18] hover:border-[#6366f1]/30 text-slate-400 transition-all duration-150 hover:scale-[1.02] active:scale-[0.97]"
        >
          <RefreshCw
            size={12}
            className={`transition-transform duration-700 ${improveSpinning ? "animate-spin" : ""}`}
          />
          Improve
        </button>

        {/* Simulate */}
        <div className="relative">
          <button
            onClick={() => { setSimOpen(o => !o); setGhOpen(false); }}
            className={[
              "btn-ripple flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#ef4444]/30 bg-[#ef4444]/10 text-[#ef4444] font-semibold transition-all duration-150 hover:bg-[#ef4444]/20 hover:scale-[1.02] active:scale-[0.97]",
              simSpring ? "animate-scale-spring" : "",
            ].join(" ")}
          >
            <Zap size={12} className={simOpen ? "text-[#ef4444]" : ""} />
            Simulate
            <ChevronDown size={11} className={`transition-transform duration-200 ${simOpen ? "rotate-180" : ""}`} />
          </button>

          {simOpen && (
            <div className="absolute right-0 top-9 z-50 w-52 rounded-xl border border-[#1e1e2e] glass shadow-xl overflow-hidden animate-slide-up">
              {SCENARIOS.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleSimulate(s.id, s.label)}
                  className="w-full text-left px-4 py-2.5 hover:bg-[#141422] border-b border-[#1e1e2e] last:border-0 transition-all duration-150 group"
                >
                  <div className="text-sm text-slate-200 group-hover:text-white transition-colors">{s.label}</div>
                  <div className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors">{s.desc}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Flash message */}
      {flash && (() => {
        const meta = FLASH_META[flash.type];
        const FlashIcon = meta.Icon;
        return (
          <div
            className="relative px-5 py-2.5 flex items-center gap-2.5 text-sm font-medium animate-slide-up overflow-hidden shrink-0"
            style={{
              background:  meta.bg,
              color:       meta.color,
              borderBottom: `1px solid ${meta.border}`,
              borderLeft:  `4px solid ${meta.color}`,
            }}
          >
            <FlashIcon size={14} className="shrink-0" />
            <span>{flash.msg}</span>

            {/* Auto-dismiss progress bar */}
            <div
              className="absolute bottom-0 left-0 h-0.5 rounded-full"
              style={{
                background: meta.color,
                animation: "flash-progress 4s linear forwards",
                transformOrigin: "left center",
              }}
            />
          </div>
        );
      })()}

      {/* Page content — slides up on mount */}
      <div className="flex-1 p-5 overflow-auto animate-slide-up">
        <MetricsDashboard metrics={metrics} history={history}>
          <IncidentPanel
            analysis={incident}
            isRollingBack={rollingBack}
            onRollback={async (depId) => {
              setRollingBack(true);
              try {
                const r = await api.rollback(depId);
                setIncident(null);
                showFlash(`✓ ${r.message}`, "ok");
              } catch {
                showFlash("Rollback failed", "err");
              } finally {
                setRollingBack(false);
              }
            }}
          />
        </MetricsDashboard>
      </div>

      {/* Backdrop for dropdowns */}
      {(simOpen || ghOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => { setSimOpen(false); setGhOpen(false); }}
        />
      )}

      {/* Inline keyframe for the flash progress bar */}
      <style>{`
        @keyframes flash-progress {
          from { width: 100%; }
          to   { width: 0%;   }
        }
      `}</style>
    </div>
  );
}
