"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import {
  Shield, Zap, GitBranch, Brain, Users, Database,
  ArrowRight, Activity, Sparkles,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────
   DATA
───────────────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: Brain,
    title: "Cognee Graph Memory",
    desc: "Every deployment and incident is stored as a knowledge graph — not just text. Causal chains like 'this commit → that crash → this rollback' are queryable in milliseconds.",
    color: "#6366f1",
  },
  {
    icon: Activity,
    title: "Live Anomaly Detection",
    desc: "Continuous monitoring of CPU, error rate, latency, and memory. When critical thresholds are crossed, Quorum fires immediately — no polling lag.",
    color: "#ef4444",
  },
  {
    icon: GitBranch,
    title: "Instant Safe-State Recall",
    desc: "Cognee's GRAPH_COMPLETION traverses the incident → root cause → deployment chain to surface the exact safe commit — without a human guessing.",
    color: "#10b981",
  },
  {
    icon: Users,
    title: "Role-Based Team Access",
    desc: "SUPER_ADMIN, ADMIN, OPERATOR, ANALYST, VIEWER. Every action is gated by role — rollbacks require OPERATOR, user management requires ADMIN.",
    color: "#f59e0b",
  },
  {
    icon: Database,
    title: "Multi-Source Ingestion",
    desc: "Connect GitHub, PagerDuty, Datadog, Slack, or push via REST. Every event is ingested into Cognee so the memory grows richer with every incident.",
    color: "#a855f7",
  },
  {
    icon: Zap,
    title: "Conversational AI Memory",
    desc: "Ask Quorum anything: 'What broke last Tuesday?', 'Which service has the most rollbacks?' Context persists across sessions via Cognee memory.",
    color: "#06b6d4",
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Connect your pipeline",
    desc: "Link GitHub, PagerDuty, or any CI source. Quorum starts building memory immediately.",
  },
  {
    step: "02",
    title: "Quorum watches everything",
    desc: "Live metrics stream in. Every deployment is remembered. Every anomaly detected in seconds.",
  },
  {
    step: "03",
    title: "AI recalls the safe state",
    desc: "When production breaks, Cognee traverses incident history to surface the exact safe commit with confidence score.",
  },
  {
    step: "04",
    title: "You confirm. System recovers.",
    desc: "AI removes error from the decision. You keep control. One click. Metrics recover.",
  },
];

const STATS = [
  { value: 6,   suffix: "s",  label: "Average detection time" },
  { value: 90,  suffix: "%",  label: "MTTR reduction" },
  { value: 3,   suffix: "x",  label: "Search types" },
  { value: 100, suffix: "%",  label: "Human-confirmed rollbacks" },
];

/* ─────────────────────────────────────────────────────────────
   ANIMATED COUNTER — fires on IntersectionObserver, not mount
───────────────────────────────────────────────────────────── */
function AnimatedCounter({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [val, setVal]           = useState(0);
  const [triggered, setTriggered] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && !triggered) setTriggered(true); },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [triggered]);

  useEffect(() => {
    if (!triggered) return;
    let current = 0;
    const step  = target / 60;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      setVal(Math.floor(current));
      if (current >= target) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [triggered, target]);

  return <span ref={ref}>{val}{suffix}</span>;
}

/* ─────────────────────────────────────────────────────────────
   LANDING PAGE
───────────────────────────────────────────────────────────── */
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const magneticRef  = useRef<HTMLAnchorElement>(null);
  const featureRefs  = useRef<(HTMLDivElement | null)[]>([]);

  /* nav glass on scroll */
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  /* scroll-reveal: add .revealed to every .reveal that enters viewport */
  useEffect(() => {
    const els = document.querySelectorAll(".reveal");
    if (!els.length) return;
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("revealed"); }),
      { threshold: 0.12 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  /* magnetic CTA button */
  const handleMagneticMove = useCallback((e: React.MouseEvent<HTMLAnchorElement>) => {
    const el = magneticRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const dx   = ((e.clientX - (rect.left + rect.width  / 2)) / rect.width)  * 18;
    const dy   = ((e.clientY - (rect.top  + rect.height / 2)) / rect.height) * 10;
    el.style.setProperty("--dx", `${dx}px`);
    el.style.setProperty("--dy", `${dy}px`);
  }, []);

  const handleMagneticLeave = useCallback(() => {
    const el = magneticRef.current;
    if (!el) return;
    el.style.setProperty("--dx", "0px");
    el.style.setProperty("--dy", "0px");
  }, []);

  /* 3-D tilt on feature cards */
  const handleTiltMove = useCallback((e: React.MouseEvent<HTMLDivElement>, idx: number) => {
    const el = featureRefs.current[idx];
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const rotX = ((e.clientY - (rect.top  + rect.height / 2)) / rect.height) * -8;
    const rotY = ((e.clientX - (rect.left + rect.width  / 2)) / rect.width)  *  8;
    el.style.setProperty("--rotX", `${rotX}deg`);
    el.style.setProperty("--rotY", `${rotY}deg`);
  }, []);

  const handleTiltLeave = useCallback((idx: number) => {
    const el = featureRefs.current[idx];
    if (!el) return;
    el.style.setProperty("--rotX", "0deg");
    el.style.setProperty("--rotY", "0deg");
    el.style.boxShadow  = "";
    el.style.borderColor = "";
  }, []);

  return (
    <div className="min-h-screen bg-[#07070d] text-white overflow-x-hidden">

      {/* ══ NAV ════════════════════════════════════════════════ */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled ? "glass border-b border-[#1e1e2e] shadow-2xl shadow-black/50" : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center shadow-lg shadow-[#6366f1]/30">
              <Shield size={16} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">Quorum</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/auth/login" className="text-sm text-slate-400 hover:text-white transition-colors px-4 py-2 rounded-xl hover:bg-white/5">
              Sign in
            </Link>
            <Link href="/auth/register" className="text-sm font-semibold px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#4f46e5] hover:shadow-lg hover:shadow-[#6366f1]/30 transition-all duration-200 active:scale-95 btn-ripple">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ══ HERO ═══════════════════════════════════════════════ */}
      <section className="relative pt-44 pb-32 px-6 text-center overflow-hidden">

        {/* Background orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-16 left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-[#6366f1]/10 rounded-full blur-[130px] animate-float" />
          <div className="absolute top-52 left-[20%] w-[380px] h-[380px] bg-[#10b981]/7 rounded-full blur-[90px] animate-float-alt" />
          <div className="absolute top-52 right-[18%] w-[320px] h-[320px] bg-[#ef4444]/6 rounded-full blur-[80px] animate-float" style={{ animationDelay: "2.5s" }} />
        </div>

        {/* Dot-grid overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.13) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
            WebkitMaskImage: "radial-gradient(ellipse 80% 65% at 50% 50%, black 30%, transparent 100%)",
            maskImage:       "radial-gradient(ellipse 80% 65% at 50% 50%, black 30%, transparent 100%)",
          }}
        />

        <div className="relative max-w-4xl mx-auto">

          {/* Badge */}
          <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full border border-[#6366f1]/30 bg-[#6366f1]/10 text-sm text-[#6366f1] font-medium mb-10 animate-fade-up">
            <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-pulse-dot" />
            ✦ Powered by Cognee Graph-Vector Memory
          </div>

          {/* H1 — three staggered lines */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-[1.1] mb-8 tracking-tight">
            <span className="block gradient-text animate-fade-up stagger-1" style={{ opacity: 0 }}>
              Quorum knows
            </span>
            <span className="block text-white animate-fade-up stagger-2" style={{ opacity: 0 }}>
              your last safe state.
            </span>
            <span className="block text-slate-500 text-4xl sm:text-5xl lg:text-6xl mt-1 animate-fade-up stagger-3" style={{ opacity: 0 }}>
              Always.
            </span>
          </h1>

          {/* Sub-headline */}
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-up stagger-4" style={{ opacity: 0 }}>
            Production incident prevention powered by AI memory. When things break,
            Quorum has already recalled the exact rollback commit — before you&apos;ve
            opened your laptop.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up stagger-5" style={{ opacity: 0 }}>
            <Link
              ref={magneticRef}
              href="/auth/register"
              className="magnetic flex items-center gap-2.5 px-9 py-4 rounded-2xl bg-gradient-to-r from-[#6366f1] to-[#4f46e5] font-bold text-lg shadow-xl shadow-[#6366f1]/25 hover:shadow-2xl hover:shadow-[#6366f1]/40 transition-all duration-200 btn-ripple glow-accent"
              onMouseMove={handleMagneticMove}
              onMouseLeave={handleMagneticLeave}
            >
              Start for free <ArrowRight size={18} />
            </Link>
            <Link
              href="/auth/login"
              className="glass flex items-center gap-2.5 px-9 py-4 rounded-2xl border border-[#1e1e2e] font-semibold text-slate-300 hover:border-[#6366f1]/40 hover:text-white transition-all duration-200"
            >
              View dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* ══ STATS ══════════════════════════════════════════════ */}
      <section className="py-16 border-y border-[#1e1e2e] bg-[#0e0e18]/60">
        <div className="max-w-5xl mx-auto px-6">
          <div className="reveal grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {STATS.map(({ value, suffix, label }) => (
              <div key={label}>
                <div className="text-4xl sm:text-5xl font-extrabold text-white mb-2 tabular-nums">
                  <AnimatedCounter target={value} suffix={suffix} />
                </div>
                <div className="text-xs uppercase tracking-widest text-slate-500 font-medium">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ HOW IT WORKS ═══════════════════════════════════════ */}
      <section className="py-28 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="reveal text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">How Quorum works</h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Four steps from chaos to recovery. The AI does the thinking. You do the confirming.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {HOW_IT_WORKS.map(({ step, title, desc }, i) => (
              <div
                key={step}
                className={`reveal card-hover relative p-6 rounded-2xl border border-[#1e1e2e] bg-[#0e0e18] hover:border-[#6366f1]/40 transition-all duration-300 overflow-hidden stagger-${i + 1}`}
              >
                {/* Ghost step number in bg */}
                <div
                  className="absolute -top-3 -right-1 text-8xl font-black text-[#6366f1] font-mono select-none pointer-events-none leading-none"
                  style={{ opacity: 0.07 }}
                >
                  {step}
                </div>
                <div className="relative">
                  <div className="text-[10px] font-mono font-bold text-[#6366f1] mb-3 tracking-[0.2em]">{step}</div>
                  <h3 className="font-bold text-white mb-2 text-sm leading-snug">{title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FEATURES ═══════════════════════════════════════════ */}
      <section className="py-28 px-6 bg-[#0e0e18]/50 border-y border-[#1e1e2e]">
        <div className="max-w-6xl mx-auto">
          <div className="reveal text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Everything you need</h2>
            <p className="text-slate-400 text-lg">
              One platform. Graph memory. Role-based teams. Multi-source ingestion.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(({ icon: Icon, title, desc, color }, i) => (
              <div
                key={title}
                ref={(el) => { featureRefs.current[i] = el; }}
                className={`reveal tilt card-hover p-6 rounded-2xl border border-[#1e1e2e] bg-[#07070d] transition-all duration-300 cursor-default stagger-${(i % 3) + 1}`}
                onMouseMove={(e)  => handleTiltMove(e, i)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow   = `0 0 32px ${color}20, 0 0 64px ${color}0a`;
                  e.currentTarget.style.borderColor = `${color}40`;
                }}
                onMouseLeave={(e) => {
                  handleTiltLeave(i);
                  e.currentTarget.style.boxShadow   = "";
                  e.currentTarget.style.borderColor = "";
                }}
              >
                <div className="w-10 h-10 rounded-xl mb-4 flex items-center justify-center" style={{ background: color + "18" }}>
                  <Icon size={20} style={{ color }} />
                </div>
                <h3 className="font-bold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ COGNEE CALLOUT ═════════════════════════════════════ */}
      <section className="py-28 px-6">
        <div className="max-w-4xl mx-auto">
          {/* Gradient border via wrapper div */}
          <div className="reveal rounded-3xl p-px bg-gradient-to-br from-[#6366f1]/40 via-[#6366f1]/10 to-transparent">
            <div className="rounded-3xl bg-gradient-to-br from-[#6366f1]/8 to-[#07070d] p-10 sm:p-14 text-center">

              {/* Brain with pulse glow */}
              <div className="animate-pulse-glow inline-flex w-16 h-16 rounded-2xl bg-[#6366f1]/20 border border-[#6366f1]/30 items-center justify-center mx-auto mb-6">
                <Brain size={32} className="text-[#6366f1]" />
              </div>

              <h2 className="text-3xl sm:text-4xl font-bold mb-4">Why not just RAG?</h2>
              <p className="text-slate-400 text-lg mb-10 max-w-2xl mx-auto leading-relaxed">
                Plain vector search finds &ldquo;similar text.&rdquo; Cognee&apos;s graph-vector hybrid traverses{" "}
                <em className="text-white not-italic">causal relationships</em>. The chain —{" "}
                <span className="text-[#6366f1] font-mono text-sm">
                  anomaly → incident → root cause → bad deploy → safe state
                </span>{" "}
                — is impossible to answer with embeddings alone.
              </p>

              {/* Chip cards */}
              <div className="grid sm:grid-cols-3 gap-4 text-sm">
                {[
                  { label: "GRAPH_COMPLETION", desc: "Full causal chain traversal",      color: "#6366f1" },
                  { label: "INSIGHTS",         desc: "Entity relationship extraction",    color: "#10b981" },
                  { label: "SUMMARIES",        desc: "High-level context recall",         color: "#f59e0b" },
                ].map(({ label, desc, color }) => (
                  <div key={label} className="card-hover p-5 rounded-xl border border-[#1e1e2e] bg-[#0e0e18] text-left">
                    <div className="font-mono font-bold text-xs mb-2 tracking-wider" style={{ color }}>{label}</div>
                    <div className="text-slate-500 text-xs leading-relaxed">{desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══ CTA ════════════════════════════════════════════════ */}
      <section className="py-24 px-6 text-center border-t border-[#1e1e2e] relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[#6366f1]/8 rounded-full blur-[120px]" />
        </div>
        <div className="relative max-w-2xl mx-auto reveal">
          <div className="inline-flex items-center gap-1.5 text-xs font-medium text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/20 px-3 py-1.5 rounded-full mb-6">
            <Sparkles size={12} />
            No credit card required
          </div>
          <h2 className="text-4xl sm:text-5xl font-extrabold mb-4 tracking-tight">
            Ready to prevent<br />
            <span className="gradient-text">the next outage?</span>
          </h2>
          <p className="text-slate-400 text-lg mb-10">
            Set up in under 5 minutes. Free forever for small teams.
          </p>
          <Link
            href="/auth/register"
            className="inline-flex items-center gap-2.5 px-12 py-4 rounded-2xl bg-gradient-to-r from-[#6366f1] to-[#4f46e5] font-bold text-lg shadow-xl shadow-[#6366f1]/25 hover:shadow-2xl hover:shadow-[#6366f1]/40 transition-all duration-200 active:scale-95 btn-ripple glow-accent"
          >
            Get started free <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ══ FOOTER ═════════════════════════════════════════════ */}
      <footer className="border-t border-[#1e1e2e] py-10 px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Shield size={14} className="text-[#6366f1]" />
            <span>Quorum — Powered by Cognee</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/auth/login"    className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Sign in</Link>
            <Link href="/auth/register" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Register</Link>
            <span className="text-slate-700 text-xs">Built for Cognee Hackathon 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
