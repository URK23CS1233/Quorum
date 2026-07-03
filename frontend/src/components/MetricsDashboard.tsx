"use client";
import { useEffect, useRef, useState } from "react";
import type { Metrics } from "@/lib/api";

// ─── Sparkline ────────────────────────────────────────────────────────────────
function Sparkline({ data, warn, crit }: { data: number[]; warn: number; crit: number }) {
  if (data.length < 2) return null;
  const W = 120, H = 32;
  const max = Math.max(...data, crit * 1.1);
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * W;
      const y = H - (v / max) * H;
      return `${x},${y}`;
    })
    .join(" ");

  const lastVal = data[data.length - 1];
  const prevPts = data[data.length - 1];
  const lastX = W;
  const lastY = H - (prevPts / max) * H;
  const color = lastVal >= crit ? "#ef4444" : lastVal >= warn ? "#f59e0b" : "#10b981";

  return (
    <svg width={W} height={H} className="opacity-70 transition-all duration-500">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        style={{ transition: "all 0.5s ease" }}
      />
      {/* Pulsing dot at the last data point */}
      <circle cx={lastX} cy={lastY} r="3" fill={color} className="animate-pulse-dot" />
      <circle
        cx={lastX}
        cy={lastY}
        r="5"
        fill="none"
        stroke={color}
        strokeWidth="1"
        opacity="0.4"
        className="animate-pulse-dot"
        style={{ animationDelay: "0.15s" }}
      />
    </svg>
  );
}

// ─── Mini Bar Graph (last 10 req/s values) ────────────────────────────────────
function MiniBarGraph({ data }: { data: number[] }) {
  const slice = data.slice(-10);
  if (slice.length < 2) return null;
  const W = 80, H = 24;
  const max = Math.max(...slice, 1);
  return (
    <svg width={W} height={H} className="opacity-70">
      {slice.map((v, i) => {
        const barH = (v / max) * H;
        const x = (i / slice.length) * W;
        const barW = W / slice.length - 1.5;
        return (
          <rect
            key={i}
            x={x}
            y={H - barH}
            width={barW}
            height={barH}
            rx="1"
            fill="#6366f1"
            opacity={0.4 + (i / slice.length) * 0.6}
            style={{ transition: "all 0.4s ease" }}
          />
        );
      })}
    </svg>
  );
}

// ─── Shimmer Skeleton ────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="rounded-xl p-4 border border-[#1e1e2e] bg-[#0e0e18] animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="h-3 w-20 rounded bg-[#1e1e2e]" />
        <div className="h-4 w-12 rounded-full bg-[#1e1e2e]" />
      </div>
      <div className="flex items-end gap-3 mb-3">
        <div className="h-7 w-16 rounded bg-[#1e1e2e]" />
        <div className="h-8 w-28 rounded bg-[#141422]" />
      </div>
      <div className="h-1.5 rounded-full bg-[#1e1e2e]" />
    </div>
  );
}

// ─── MetricCard ───────────────────────────────────────────────────────────────
interface MetricCardProps {
  label: string;
  value: string;
  pct: number;
  warn: number;
  crit: number;
  history: number[];
  unit: string;
  index: number;
}

function MetricCard({ label, value, pct, warn, crit, history, unit, index }: MetricCardProps) {
  const numVal = parseFloat(value);
  const isCrit = numVal >= crit;
  const isWarn = !isCrit && numVal >= warn;
  const color = isCrit ? "#ef4444" : isWarn ? "#f59e0b" : "#10b981";
  const glow = isCrit ? "gauge-critical" : isWarn ? "gauge-degraded" : "gauge-healthy";
  const barPct = Math.min((pct / crit) * 100, 100);

  const valueRef = useRef<HTMLSpanElement>(null);
  const badgeRef = useRef<HTMLSpanElement>(null);
  const prevStatus = useRef<string>("");

  const stagger = `stagger-${Math.min(index + 1, 6)}` as const;

  // Flash value on change
  useEffect(() => {
    const el = valueRef.current;
    if (!el) return;
    el.classList.add("animate-count-flash");
    const t = setTimeout(() => el.classList.remove("animate-count-flash"), 500);
    return () => clearTimeout(t);
  }, [value]);

  // Spring-scale badge when status changes to CRITICAL
  const currentStatus = isCrit ? "CRITICAL" : isWarn ? "WARN" : "OK";
  useEffect(() => {
    if (currentStatus === "CRITICAL" && prevStatus.current !== "CRITICAL") {
      const el = badgeRef.current;
      if (!el) return;
      el.classList.add("animate-scale-spring");
      const t = setTimeout(() => el.classList.remove("animate-scale-spring"), 600);
      return () => clearTimeout(t);
    }
    prevStatus.current = currentStatus;
  }, [currentStatus]);

  return (
    <div
      className={`
        rounded-xl p-4 border border-[#1e1e2e] bg-[#0e0e18]
        transition-all duration-300
        card-hover
        animate-slide-up ${stagger}
        ${glow}
        ${isCrit ? "animate-incident" : ""}
        group
      `}
      style={{ "--card-accent": color } as React.CSSProperties}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">{label}</span>
        <span
          ref={badgeRef}
          className={`text-xs px-2 py-0.5 rounded-full font-semibold transition-all duration-300 ${isCrit ? "animate-scale-spring" : ""}`}
          style={{ background: color + "22", color }}
        >
          {currentStatus}
        </span>
      </div>

      <div className="flex items-end gap-3">
        <span ref={valueRef} className="text-2xl font-bold font-mono transition-all duration-200" style={{ color }}>
          {value}
          <span className="text-xs ml-1 text-slate-500">{unit}</span>
        </span>
        <Sparkline data={history} warn={warn} crit={crit} />
      </div>

      {/* Progress bar — keyed on barPct so DOM remounts and re-animates on big jumps */}
      <div className="mt-3 h-1.5 rounded-full bg-[#1e1e2e] overflow-hidden">
        <div
          key={Math.round(barPct / 5)}
          className="h-full rounded-full animate-bar-fill"
          style={{ width: `${barPct}%`, background: color }}
        />
      </div>

      {/* Hover accent line */}
      <div
        className="absolute inset-x-0 bottom-0 h-px rounded-b-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
      />
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
interface Props {
  metrics: Metrics | null;
  history: Metrics[];
  children?: React.ReactNode;
}

export default function MetricsDashboard({ metrics, history, children }: Props) {
  const hist = (key: keyof Metrics) => history.slice(-30).map((m) => m[key] as number);

  const reqsHistory = history.slice(-10).map((m) => m.requests_per_second as number);
  const reqsRef = useRef<HTMLSpanElement>(null);
  const prevReqs = useRef<string>("");

  useEffect(() => {
    if (!metrics) return;
    const cur = metrics.requests_per_second.toFixed(0);
    if (cur !== prevReqs.current) {
      const el = reqsRef.current;
      if (el) {
        el.classList.add("animate-scale-spring");
        setTimeout(() => el?.classList.remove("animate-scale-spring"), 400);
      }
      prevReqs.current = cur;
    }
  }, [metrics?.requests_per_second]);

  // Loading shimmer
  if (!metrics) {
    return (
      <div className="flex gap-4 h-full">
        <div className="flex-1 grid grid-cols-2 gap-4 content-start">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <div className="col-span-2 rounded-xl p-3 border border-[#1e1e2e] bg-[#0e0e18] animate-pulse h-14" />
        </div>
        <div className="w-96 shrink-0">{children}</div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 h-full">
      <div className="flex-1 grid grid-cols-2 gap-4 content-start">
        <MetricCard
          index={0}
          label="CPU Usage"
          value={metrics.cpu.toFixed(1)}
          pct={metrics.cpu}
          warn={65}
          crit={85}
          history={hist("cpu")}
          unit="%"
        />
        <MetricCard
          index={1}
          label="Error Rate"
          value={metrics.error_rate.toFixed(2)}
          pct={metrics.error_rate}
          warn={1.5}
          crit={5.0}
          history={hist("error_rate")}
          unit="%"
        />
        <MetricCard
          index={2}
          label="Latency P99"
          value={metrics.latency_p99.toFixed(0)}
          pct={metrics.latency_p99}
          warn={500}
          crit={2000}
          history={hist("latency_p99")}
          unit="ms"
        />
        <MetricCard
          index={3}
          label="Memory"
          value={metrics.memory_usage.toFixed(1)}
          pct={metrics.memory_usage}
          warn={75}
          crit={90}
          history={hist("memory_usage")}
          unit="%"
        />

        {/* Bottom stats row */}
        <div className="col-span-2 rounded-xl p-3 border border-[#1e1e2e] bg-[#0e0e18] flex items-center gap-4 animate-slide-up stagger-5">
          <div className="flex flex-col items-center">
            <span className="text-xs text-slate-500 uppercase tracking-widest">Req/s</span>
            <span
              ref={reqsRef}
              className="text-lg font-bold font-mono text-slate-300 transition-all duration-200 inline-block"
            >
              {metrics.requests_per_second.toFixed(0)}
            </span>
          </div>
          <div className="w-px h-8 bg-[#1e1e2e]" />
          <MiniBarGraph data={reqsHistory} />
          <div className="w-px h-8 bg-[#1e1e2e]" />
          <div className="text-xs text-slate-500">
            Last update:{" "}
            <span className="text-slate-400 font-mono">
              {new Date(metrics.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      <div className="w-96 shrink-0">{children}</div>
    </div>
  );
}
