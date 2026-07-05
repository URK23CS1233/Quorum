"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { Shield, ArrowRight, Clock, GitBranch, Zap, Brain, Activity } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   QUANTUM VORTEX CANVAS
═══════════════════════════════════════════════════════════════ */
function QuantumCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d") as CanvasRenderingContext2D;
    if (!ctx) return;

    let W = canvas.width  = window.innerWidth;
    let H = canvas.height = window.innerHeight;
    let animId: number;
    let t = 0;

    // Commit particles
    const particles: {
      x: number; y: number; vx: number; vy: number;
      r: number; alpha: number; color: string; trail: {x:number;y:number}[];
    }[] = [];

    const COLORS = ["#6366f1","#00d4ff","#10b981","#7c3aed","#a78bfa"];

    for (let i = 0; i < 120; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 2 + 0.5,
        alpha: Math.random() * 0.6 + 0.2,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        trail: [],
      });
    }

    // Ring pulses
    const rings: { r: number; max: number; alpha: number; color: string }[] = [];
    let ringTimer = 0;

    function spawnRing() {
      rings.push({ r: 0, max: Math.max(W, H) * 0.7, alpha: 0.6,
        color: COLORS[Math.floor(Math.random() * COLORS.length)] });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      t += 0.008;

      // Deep space bg gradient
      const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W,H)*0.8);
      grad.addColorStop(0,   "rgba(12,8,40,0.95)");
      grad.addColorStop(0.5, "rgba(4,4,20,0.98)");
      grad.addColorStop(1,   "rgba(0,0,8,1)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Star field
      ctx.save();
      for (let i = 0; i < 200; i++) {
        const sx = ((i * 137.508 * W) % W + W) % W;
        const sy = ((i * 97.3 * H)  % H + H) % H;
        const blink = Math.sin(t * 1.5 + i) * 0.5 + 0.5;
        ctx.globalAlpha = blink * 0.7 + 0.1;
        ctx.fillStyle = i % 5 === 0 ? "#a78bfa" : "#ffffff";
        ctx.beginPath();
        ctx.arc(sx, sy, i % 7 === 0 ? 1.2 : 0.6, 0, Math.PI*2);
        ctx.fill();
      }
      ctx.restore();

      // Vortex at centre
      const cx = W / 2, cy = H / 2;
      for (let ring = 8; ring > 0; ring--) {
        const phase = t * (ring * 0.3) + ring;
        const rr = ring * 38 + Math.sin(phase) * 12;
        const grd = ctx.createRadialGradient(cx, cy, rr*0.5, cx, cy, rr);
        grd.addColorStop(0, `rgba(99,102,241,${0.018 * ring})`);
        grd.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(cx, cy, rr, 0, Math.PI*2);
        ctx.strokeStyle = `rgba(99,102,241,${0.07 + ring*0.012})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.fillStyle = grd;
        ctx.fill();
      }

      // Rotating vortex lines
      for (let arm = 0; arm < 6; arm++) {
        const angle = (arm / 6) * Math.PI * 2 + t * 0.6;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle);
        const lg = ctx.createLinearGradient(0, 0, 220, 0);
        lg.addColorStop(0, "rgba(99,102,241,0.5)");
        lg.addColorStop(0.6, "rgba(124,58,237,0.18)");
        lg.addColorStop(1, "transparent");
        ctx.strokeStyle = lg;
        ctx.lineWidth = arm % 2 === 0 ? 1.5 : 0.8;
        ctx.beginPath();
        ctx.moveTo(18, 0);
        ctx.bezierCurveTo(60, arm*10-30, 130, -arm*8+20, 220, 0);
        ctx.stroke();
        ctx.restore();
      }

      // Inner quantum core
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 55);
      coreGrad.addColorStop(0, "rgba(167,139,250,0.22)");
      coreGrad.addColorStop(0.5, "rgba(99,102,241,0.08)");
      coreGrad.addColorStop(1, "transparent");
      ctx.beginPath();
      ctx.arc(cx, cy, 55, 0, Math.PI*2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Particles + trails
      particles.forEach((p) => {
        // Pull toward vortex
        const dx = cx - p.x, dy = cy - p.y;
        const dist = Math.sqrt(dx*dx+dy*dy);
        const pull = Math.max(0, 1 - dist/480) * 0.04;
        p.vx += dx/dist * pull;
        p.vy += dy/dist * pull;

        // Orbit boost near core
        if (dist < 100) {
          p.vx += -dy/dist * 0.08;
          p.vy +=  dx/dist * 0.08;
        }

        p.x += p.vx; p.y += p.vy;
        p.trail.push({x:p.x, y:p.y});
        if (p.trail.length > 12) p.trail.shift();

        // Wrap
        if (p.x<0) p.x=W; if (p.x>W) p.x=0;
        if (p.y<0) p.y=H; if (p.y>H) p.y=0;

        // Trail
        if (p.trail.length > 1) {
          ctx.beginPath();
          ctx.moveTo(p.trail[0].x, p.trail[0].y);
          p.trail.forEach(pt => ctx.lineTo(pt.x, pt.y));
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = p.alpha * 0.3;
          ctx.lineWidth = p.r * 0.7;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // Dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      // Expanding ring pulses
      ringTimer++;
      if (ringTimer % 90 === 0) spawnRing();
      for (let i = rings.length-1; i>=0; i--) {
        const rg = rings[i];
        rg.r += 2.2;
        rg.alpha *= 0.984;
        if (rg.alpha < 0.01 || rg.r > rg.max) { rings.splice(i,1); continue; }
        ctx.beginPath();
        ctx.arc(cx, cy, rg.r, 0, Math.PI*2);
        ctx.strokeStyle = rg.color;
        ctx.globalAlpha = rg.alpha * 0.25;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      animId = requestAnimationFrame(draw);
    }

    draw();
    spawnRing();

    const onResize = () => {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", onResize); };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ opacity: 0.85 }}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════
   GLITCH TEXT
═══════════════════════════════════════════════════════════════ */
function GlitchText({ text, className = "" }: { text: string; className?: string }) {
  return (
    <span className={`relative inline-block ${className}`} data-text={text}
      style={{
        textShadow: "0.05em 0 0 rgba(239,68,68,0.6), -0.025em -0.05em 0 rgba(99,102,241,0.5), 0.025em 0.05em 0 rgba(16,185,129,0.5)",
        animation: "glitch 3s infinite",
      }}>
      {text}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   GLASS SHATTER
═══════════════════════════════════════════════════════════════ */

// Shard polygon regions — together they tile the full bounding box
const SHARDS = [
  { clip:"polygon(0% 0%, 42% 0%, 30% 44%, 0% 32%)",               dx:-72, dy:-95, rot:-24, delay:0.00 },
  { clip:"polygon(42% 0%, 70% 0%, 62% 28%, 30% 44%)",              dx:  2, dy:-115,rot: 16, delay:0.02 },
  { clip:"polygon(70% 0%, 100% 0%, 100% 30%, 80% 40%, 62% 28%)",   dx: 95, dy:-82, rot: 21, delay:0.01 },
  { clip:"polygon(0% 32%, 30% 44%, 18% 70%, 0% 100%)",             dx:-105,dy: 18, rot:-32, delay:0.03 },
  { clip:"polygon(30% 44%, 62% 28%, 50% 62%, 18% 70%)",            dx:-22, dy: 72, rot: 13, delay:0.04 },
  { clip:"polygon(62% 28%, 80% 40%, 68% 68%, 50% 62%)",            dx: 26, dy: 92, rot:-11, delay:0.02 },
  { clip:"polygon(80% 40%, 100% 30%, 100% 100%, 68% 68%)",         dx:115, dy: 38, rot: 27, delay:0.03 },
  { clip:"polygon(18% 70%, 50% 62%, 38% 100%, 0% 100%)",           dx:-58, dy:105, rot:-22, delay:0.05 },
  { clip:"polygon(50% 62%, 68% 68%, 58% 100%, 38% 100%)",          dx: 12, dy:115, rot:  7, delay:0.04 },
  { clip:"polygon(68% 68%, 100% 100%, 58% 100%)",                  dx: 85, dy:108, rot: 32, delay:0.01 },
];

// SVG paths along shard boundaries — visible as crack lines
const CRACKS = [
  "M30 44 L42 0", "M42 0 L70 0", "M70 0 L62 28",
  "M62 28 L80 40", "M80 40 L100 30",
  "M62 28 L30 44", "M30 44 L0 32",
  "M30 44 L18 70", "M18 70 L0 100",
  "M18 70 L50 62", "M50 62 L38 100",
  "M50 62 L68 68", "M68 68 L58 100",
  "M68 68 L100 100", "M80 40 L68 68",
].join(" ");

function GlassShatter({ text, className = "" }: { text: string; className?: string }) {
  const [phase, setPhase] = useState<"intact"|"cracking"|"shattered">("intact");

  useEffect(() => {
    const run = () => {
      setPhase("cracking");
      setTimeout(() => setPhase("shattered"), 160);
      setTimeout(() => setPhase("intact"),    1900);
    };
    const t = setTimeout(run, 1800);            // first shatter
    const iv = setInterval(run, 5800);          // loop every ~6s
    return () => { clearTimeout(t); clearInterval(iv); };
  }, []);

  const shattered = phase === "shattered";
  const cracking  = phase === "cracking";

  return (
    <span
      className={`relative inline-block select-none ${className}`}
      style={{
        perspective: "900px",
        transform: cracking ? "scale(1.02)" : "scale(1)",
        filter: cracking
          ? "brightness(2) drop-shadow(0 0 12px rgba(255,255,255,0.9))"
          : "none",
        transition: "transform 0.12s ease, filter 0.12s ease",
      }}>

      {/* Invisible spacer — holds layout width/height */}
      <span style={{ visibility:"hidden" }}>{text}</span>

      {/* Crack lines — flash on during cracking phase */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ opacity: cracking ? 1 : 0, transition:"opacity 0.1s ease" }}>
        <path d={CRACKS} stroke="rgba(255,255,255,0.95)" strokeWidth="0.7"
          fill="none" strokeLinecap="round" />
        {/* Glint dots at crack intersections */}
        {[[30,44],[62,28],[50,62],[68,68],[80,40],[18,70]].map(([cx,cy],i)=>(
          <circle key={i} cx={cx} cy={cy} r="1.5"
            fill="rgba(255,255,255,0.9)" />
        ))}
      </svg>

      {/* Glass shards — each shows the full text clipped to its polygon */}
      {SHARDS.map(({ clip, dx, dy, rot, delay }, i) => (
        <span
          key={i}
          aria-hidden
          className="absolute inset-0 whitespace-nowrap"
          style={{
            clipPath: clip,
            transform: shattered
              ? `translate(${dx}px, ${dy}px) rotate(${rot}deg)`
              : "translate(0px,0px) rotate(0deg)",
            opacity: shattered ? 0 : 1,
            transition: shattered
              ? `transform 0.58s cubic-bezier(0.22,1,0.36,1) ${delay}s,
                 opacity   0.48s ease                         ${0.12+delay}s`
              : `transform 0.55s cubic-bezier(0.34,1.56,0.64,1) ${delay*0.4}s,
                 opacity   0.28s ease                            ${delay*0.4}s`,
            filter: "drop-shadow(1px 3px 5px rgba(0,0,0,0.7))",
          }}>
          {text}
        </span>
      ))}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   TYPEWRITER
═══════════════════════════════════════════════════════════════ */
function Typewriter({ lines, className = "" }: { lines: string[]; className?: string }) {
  const [displayed, setDisplayed] = useState("");
  const [lineIdx, setLineIdx]     = useState(0);
  const [charIdx, setCharIdx]     = useState(0);
  const [done, setDone]           = useState(false);

  useEffect(() => {
    if (done) return;
    const current = lines[lineIdx];
    if (!current) return;
    if (charIdx < current.length) {
      const t = setTimeout(() => {
        setDisplayed(prev => prev + current[charIdx]);
        setCharIdx(c => c + 1);
      }, 38);
      return () => clearTimeout(t);
    } else {
      if (lineIdx < lines.length - 1) {
        const t = setTimeout(() => {
          setDisplayed(prev => prev + "\n");
          setLineIdx(l => l + 1);
          setCharIdx(0);
        }, 420);
        return () => clearTimeout(t);
      } else {
        setDone(true);
      }
    }
  }, [charIdx, lineIdx, lines, done]);

  return (
    <pre className={`font-mono text-xs leading-relaxed whitespace-pre-wrap ${className}`}>
      {displayed}
      {!done && <span className="animate-pulse text-[#00d4ff]">▋</span>}
    </pre>
  );
}

/* ═══════════════════════════════════════════════════════════════
   TIMELINE VISUALISER
═══════════════════════════════════════════════════════════════ */
const COMMITS = [
  { id:"a1b2c3", msg:"Add Redis cache layer",          time:"-4h", safe:true  },
  { id:"d4e5f6", msg:"Auth service async migration",   time:"-2h", safe:false },
  { id:"g7h8i9", msg:"Payment index optimisation",     time:"-30m",safe:true  },
];

function TemporalTimeline() {
  const [active, setActive] = useState<number|null>(null);
  const [playing, setPlaying] = useState(false);
  const [restored, setRestored] = useState(false);

  const handlePlay = () => {
    setPlaying(true);
    setRestored(false);
    setActive(0);
    setTimeout(()=>setActive(1), 800);
    setTimeout(()=>{ setActive(2); }, 1600);
    setTimeout(()=>{ setRestored(true); setPlaying(false); }, 2800);
  };

  return (
    <div className="relative p-8 rounded-3xl overflow-hidden"
      style={{
        background:"linear-gradient(135deg,rgba(12,8,40,0.95),rgba(4,4,20,0.98))",
        border:"1px solid rgba(99,102,241,0.2)",
        boxShadow:"0 0 80px rgba(99,102,241,0.08), inset 0 1px 0 rgba(255,255,255,0.04)",
      }}>

      {/* Scanlines */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:"repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,212,255,0.015) 2px,rgba(0,212,255,0.015) 4px)",
        }} />

      <div className="relative">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-2 h-2 rounded-full bg-[#ef4444] animate-pulse" />
          <span className="font-mono text-xs text-[#ef4444] tracking-[0.25em] uppercase">
            {restored ? "TIMELINE RESTORED" : playing ? "SCANNING TEMPORAL GRAPH…" : "INCIDENT DETECTED · 03:47 UTC"}
          </span>
        </div>

        {/* Timeline rail */}
        <div className="relative flex items-center gap-0 mb-8">
          <div className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#6366f1]/40 to-transparent" />
          {COMMITS.map((c, i) => (
            <div key={c.id} className="flex-1 flex flex-col items-center relative">
              {/* Node */}
              <div
                onClick={() => setActive(i)}
                className="relative z-10 w-10 h-10 rounded-full flex items-center justify-center cursor-pointer transition-all duration-500 mb-3"
                style={{
                  background: active !== null && i <= active
                    ? (c.safe ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)")
                    : "rgba(30,30,46,0.8)",
                  border: `2px solid ${active !== null && i <= active
                    ? (c.safe ? "#10b981" : "#ef4444")
                    : "rgba(99,102,241,0.3)"}`,
                  boxShadow: active === i
                    ? `0 0 24px ${c.safe ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.5)"}`
                    : "none",
                  transform: active === i ? "scale(1.2)" : "scale(1)",
                }}>
                <GitBranch size={14} style={{
                  color: active !== null && i <= active ? (c.safe ? "#10b981" : "#ef4444") : "#4b5563"
                }}/>
                {/* Rollback target glow */}
                {restored && i === 0 && (
                  <div className="absolute -inset-2 rounded-full border-2 border-[#10b981] animate-ping opacity-60" />
                )}
              </div>
              <div className="text-center">
                <div className="font-mono text-[10px] text-slate-500">{c.time}</div>
                <div className="font-mono text-[10px] font-bold" style={{
                  color: active !== null && i <= active ? (c.safe ? "#10b981" : "#ef4444") : "#374151"
                }}>{c.id}</div>
                <div className="text-[10px] text-slate-600 max-w-[90px] leading-tight mt-1">{c.msg}</div>
              </div>

              {/* Connector line */}
              {i < COMMITS.length - 1 && (
                <div className="absolute top-5 left-1/2 w-full h-px transition-all duration-700"
                  style={{
                    background: active !== null && i < active
                      ? "linear-gradient(90deg,#10b981,#6366f1)"
                      : "rgba(99,102,241,0.15)",
                  }} />
              )}
            </div>
          ))}
        </div>

        {/* Status terminal */}
        <div className="rounded-xl p-4 font-mono text-xs leading-relaxed"
          style={{background:"rgba(0,0,0,0.5)", border:"1px solid rgba(0,212,255,0.1)"}}>
          {!playing && !restored && (
            <span className="text-[#ef4444]">
              [03:47:12] ANOMALY · error_rate=18.4% cpu=91% latency=4200ms<br/>
              [03:47:14] ROOT_CAUSE: auth-service async driver · connection pool exhausted<br/>
              [03:47:15] QUORUM: initiating temporal graph scan…
            </span>
          )}
          {playing && (
            <Typewriter className="text-[#00d4ff]" lines={[
              "[SCAN] traversing deployment graph…",
              "[GRAPH] dep-002 → caused → INC-001",
              "[GRAPH] INC-001 → safe rollback → dep-001 (a1b2c3)",
              "[QUORUM] safe state identified · confidence: HIGH",
            ]} />
          )}
          {restored && (
            <span>
              <span className="text-[#10b981]">
                [03:47:31] ROLLBACK COMPLETE · commit a1b2c3d4{"\n"}
                [03:47:32] error_rate=0.1% · cpu=22% · latency=180ms{"\n"}
              </span>
              <span className="text-[#6366f1]">
                [03:47:32] ✦ TIMELINE RESTORED — 19 minutes before incident
              </span>
            </span>
          )}
        </div>

        <button
          onClick={handlePlay}
          disabled={playing}
          className="mt-5 btn-ripple flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold tracking-widest uppercase transition-all duration-300"
          style={{
            background: playing ? "rgba(30,30,46,0.8)" : "linear-gradient(135deg,#6366f1,#7c3aed)",
            border: playing ? "1px solid rgba(99,102,241,0.3)" : "none",
            color: playing ? "#4b5563" : "white",
            boxShadow: playing ? "none" : "0 0 24px rgba(99,102,241,0.4)",
          }}>
          <Clock size={13} />
          {restored ? "Replay Time Heist" : playing ? "Scanning…" : "Initiate Temporal Scan"}
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   LANDING PAGE
═══════════════════════════════════════════════════════════════ */
const STORY_BEATS = [
  { phase:"T-00:00", label:"INCIDENT DETECTED",    color:"#ef4444", desc:"CPU 91% · Error rate 18% · Latency 4200ms · Engineers paged" },
  { phase:"T+00:19", label:"GRAPH TRAVERSAL",      color:"#6366f1", desc:"Cognee scans causal chains across all deployment memory" },
  { phase:"T+00:23", label:"SAFE STATE FOUND",     color:"#00d4ff", desc:"commit a1b2c3 · 4 hours ago · confidence HIGH" },
  { phase:"T+00:31", label:"TIMELINE RESTORED",    color:"#10b981", desc:"One click. Human confirmed. System recovered." },
];

const FEATURES = [
  { icon: Brain,    title:"Graph-Vector Memory",    desc:"Every deployment, every incident — stored as a causal knowledge graph. Not text. Not embeddings. Relationships.", color:"#6366f1" },
  { icon: Activity, title:"Live Anomaly Detection", desc:"CPU, error rate, latency, memory — streamed in real time. Threshold breach fires in under 6 seconds.", color:"#ef4444" },
  { icon: GitBranch,title:"Instant Safe-State Recall",desc:"GRAPH_COMPLETION traverses the incident → cause → deployment chain to surface the exact rollback commit.", color:"#10b981" },
  { icon: Zap,      title:"Conversational AI",      desc:"Ask anything. 'What broke last Tuesday?' 'Which service has the most rollbacks?' Context persists across sessions.", color:"#00d4ff" },
  { icon: Clock,    title:"Temporal Confidence Score",desc:"Every recall includes a confidence level. High = the graph has seen this before. Low = seed more incident history.", color:"#f59e0b" },
  { icon: Shield,   title:"Human-Confirmed Rollbacks",desc:"AI removes error from the decision. You keep control. Rollback requires OPERATOR role. One click. Done.", color:"#a855f7" },
];

export default function LandingPage() {
  const [scrollY, setScrollY]     = useState(0);
  const [mounted, setMounted]     = useState(false);
  const featureRefs = useRef<(HTMLDivElement|null)[]>([]);

  useEffect(() => {
    setMounted(true);
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Scroll-reveal
  useEffect(() => {
    if (!mounted) return;
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add("revealed"); }),
      { threshold: 0.1 }
    );
    document.querySelectorAll(".reveal").forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, [mounted]);

  // 3D tilt
  const handleTilt = useCallback((e: React.MouseEvent<HTMLDivElement>, i: number) => {
    const el = featureRefs.current[i];
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--rotX", `${((e.clientY-(r.top+r.height/2))/r.height)*-8}deg`);
    el.style.setProperty("--rotY", `${((e.clientX-(r.left+r.width/2))/r.width)*8}deg`);
  }, []);

  const handleTiltLeave = useCallback((i: number) => {
    const el = featureRefs.current[i];
    if (!el) return;
    el.style.setProperty("--rotX","0deg");
    el.style.setProperty("--rotY","0deg");
  }, []);

  return (
    <div className="min-h-screen bg-[#000008] text-white overflow-x-hidden">

      {/* Inject cinematic keyframes */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes glitch {
          0%,94%,100% { text-shadow: 0.05em 0 0 rgba(239,68,68,0.6), -0.025em -0.05em 0 rgba(99,102,241,0.5); }
          95%  { text-shadow: -0.05em -0.025em 0 rgba(239,68,68,0.7), 0.025em 0.05em 0 rgba(0,212,255,0.5); clip-path: inset(40% 0 40% 0); }
          96%  { text-shadow: 0.05em 0.025em 0 rgba(99,102,241,0.7), -0.05em -0.05em 0 rgba(16,185,129,0.5); }
          97%  { clip-path: inset(0); }
        }
        @keyframes floatY {
          0%,100% { transform:translateY(0); }
          50%     { transform:translateY(-18px); }
        }
        @keyframes floatY2 {
          0%,100% { transform:translateY(0) rotate(0deg); }
          50%     { transform:translateY(-12px) rotate(1.5deg); }
        }
        @keyframes quantumPulse {
          0%,100% { box-shadow:0 0 0 0 rgba(99,102,241,0.5), 0 0 40px rgba(99,102,241,0.15); }
          50%     { box-shadow:0 0 0 16px rgba(99,102,241,0), 0 0 80px rgba(99,102,241,0.35); }
        }
        @keyframes scanline {
          0%   { transform:translateY(-100%); }
          100% { transform:translateY(100vh); }
        }
        @keyframes orbit {
          from { transform:rotate(0deg) translateX(90px) rotate(0deg); }
          to   { transform:rotate(360deg) translateX(90px) rotate(-360deg); }
        }
        @keyframes orbit2 {
          from { transform:rotate(180deg) translateX(130px) rotate(-180deg); }
          to   { transform:rotate(540deg) translateX(130px) rotate(-540deg); }
        }
        @keyframes timeRipple {
          0%   { transform:scale(1);   opacity:0.6; }
          100% { transform:scale(2.5); opacity:0; }
        }
        @keyframes slideUpFade {
          from { opacity:0; transform:translateY(32px); }
          to   { opacity:1; transform:translateY(0); }
        }
        @keyframes shimmerText {
          0%   { background-position:0% 50%; }
          50%  { background-position:100% 50%; }
          100% { background-position:0% 50%; }
        }
        .temporal-gradient {
          background: linear-gradient(135deg, #6366f1 0%, #00d4ff 30%, #10b981 60%, #7c3aed 100%);
          background-size: 300% 300%;
          animation: shimmerText 4s ease infinite;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .quantum-border {
          position:relative;
        }
        .quantum-border::before {
          content:'';
          position:absolute;
          inset:-1px;
          border-radius:inherit;
          padding:1px;
          background:linear-gradient(135deg,rgba(99,102,241,0.5),rgba(0,212,255,0.3),rgba(16,185,129,0.2));
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
        }
        .reveal { opacity:0; transform:translateY(28px); transition:opacity 0.7s ease, transform 0.7s ease; }
        .reveal.revealed { opacity:1; transform:translateY(0); }
        .reveal.stagger-1.revealed { transition-delay:0.05s; }
        .reveal.stagger-2.revealed { transition-delay:0.12s; }
        .reveal.stagger-3.revealed { transition-delay:0.19s; }
        .reveal.stagger-4.revealed { transition-delay:0.26s; }
        .reveal.stagger-5.revealed { transition-delay:0.33s; }
        .reveal.stagger-6.revealed { transition-delay:0.40s; }
        .tilt { transform:perspective(900px) rotateX(var(--rotX,0deg)) rotateY(var(--rotY,0deg)); transition:transform 0.12s ease; }
        .btn-primary {
          background:linear-gradient(135deg,#6366f1,#4f46e5);
          box-shadow:0 0 0 0 rgba(99,102,241,0.5);
          animation:quantumPulse 2.5s ease-in-out infinite;
          transition:all 0.2s;
        }
        .btn-primary:hover { transform:scale(1.04); box-shadow:0 8px 40px rgba(99,102,241,0.5); }
        .btn-primary:active { transform:scale(0.97); }
      `}} />

      {/* ── NAV ─────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 transition-all duration-500"
        style={{
          background: scrollY > 30 ? "rgba(0,0,8,0.85)" : "transparent",
          backdropFilter: scrollY > 30 ? "blur(20px)" : "none",
          borderBottom: scrollY > 30 ? "1px solid rgba(99,102,241,0.15)" : "none",
        }}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 rounded-xl flex items-center justify-center"
              style={{background:"linear-gradient(135deg,#6366f1,#4f46e5)", boxShadow:"0 0 20px rgba(99,102,241,0.5)"}}>
              <Shield size={17} className="text-white" />
              <div className="absolute inset-0 rounded-xl animate-ping opacity-20"
                style={{background:"#6366f1"}} />
            </div>
            <span className="font-bold text-lg tracking-tight">
              <span className="temporal-gradient">Quorum</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/auth/login" className="text-sm text-slate-400 hover:text-white transition-colors px-4 py-2">
              Sign in
            </Link>
            <Link href="/auth/register"
              className="btn-primary text-sm font-bold px-5 py-2.5 rounded-xl text-white">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center text-center overflow-hidden">

        {/* Quantum canvas bg */}
        <QuantumCanvas />

        {/* Scanline sweep */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div style={{
            position:"absolute", left:0, right:0, height:"2px",
            background:"linear-gradient(90deg,transparent,rgba(0,212,255,0.3),transparent)",
            animation:"scanline 6s linear infinite",
          }} />
        </div>

        {/* Orbiting dots around vortex */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-0 h-0">
            {[0,1,2].map(i=>(
              <div key={i} className="absolute w-2.5 h-2.5 rounded-full"
                style={{
                  background:["#6366f1","#00d4ff","#10b981"][i],
                  boxShadow:`0 0 12px ${["rgba(99,102,241,0.8)","rgba(0,212,255,0.8)","rgba(16,185,129,0.8)"][i]}`,
                  animation:`orbit${i===1?"2":""} ${5+i*1.5}s linear infinite`,
                  animationDelay:`${i*-1.2}s`,
                }} />
            ))}
          </div>
        </div>

        {/* Hero content */}
        <div className="relative z-10 max-w-5xl mx-auto px-6 pt-20">

          {/* Incident badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-10 font-mono text-xs tracking-widest"
            style={{
              background:"rgba(239,68,68,0.08)",
              border:"1px solid rgba(239,68,68,0.3)",
              color:"#ef4444",
              animation:"slideUpFade 0.8s ease both",
            }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444] animate-pulse" />
            PRODUCTION INCIDENT · T+00:00 · TIMELINE COMPROMISED
          </div>

          {/* Main headline */}
          <h1 className="text-6xl sm:text-7xl lg:text-8xl font-black leading-[1.0] mb-6 tracking-tight">
            <span className="block text-white"
              style={{animation:"slideUpFade 0.8s 0.1s ease both", opacity:0}}>
              When the future
            </span>
            <span className="block"
              style={{animation:"slideUpFade 0.8s 0.2s ease both", opacity:0}}>
              <GlassShatter text="breaks," className="text-white" />
            </span>
            <span className="block"
              style={{animation:"slideUpFade 0.8s 0.35s ease both", opacity:0}}>
              <span className="temporal-gradient">we rewrite the past.</span>
            </span>
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed"
            style={{animation:"slideUpFade 0.8s 0.5s ease both", opacity:0}}>
            Quorum uses Cognee graph-vector memory to time-travel through your
            deployment history — surfacing the exact safe state before you&apos;ve
            opened your laptop.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4"
            style={{animation:"slideUpFade 0.8s 0.65s ease both", opacity:0}}>
            <Link href="/auth/register" className="btn-primary flex items-center gap-2.5 px-10 py-4 rounded-2xl font-bold text-lg text-white">
              Enter the Quantum Realm <ArrowRight size={18} />
            </Link>
            <Link href="/auth/login"
              className="flex items-center gap-2.5 px-10 py-4 rounded-2xl font-semibold text-slate-300 transition-all duration-200 hover:text-white hover:bg-white/5"
              style={{border:"1px solid rgba(99,102,241,0.2)"}}>
              View live dashboard
            </Link>
          </div>

          {/* Scroll indicator */}
          <div className="mt-20 flex flex-col items-center gap-2 opacity-40"
            style={{animation:"slideUpFade 0.8s 1s ease both", opacity:0}}>
            <span className="font-mono text-[10px] tracking-[0.3em] text-slate-500 uppercase">Scroll to witness</span>
            <div className="w-px h-12 bg-gradient-to-b from-[#6366f1] to-transparent animate-pulse" />
          </div>
        </div>
      </section>

      {/* ── STORY: THE INCIDENT ─────────────────────────────── */}
      <section className="py-32 px-6 relative overflow-hidden"
        style={{background:"linear-gradient(180deg,#000008 0%,#0a0014 50%,#000008 100%)"}}>

        <div className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage:"radial-gradient(circle at 50% 50%, rgba(239,68,68,0.06) 0%, transparent 70%)",
          }} />

        <div className="max-w-6xl mx-auto">
          <div className="reveal text-center mb-20">
            <div className="font-mono text-xs tracking-[0.4em] text-[#ef4444] mb-4 uppercase">Chapter 01 · The Snap</div>
            <h2 className="text-4xl sm:text-5xl font-black mb-4">
              <GlassShatter text="3:47 AM." className="text-white" />
              {" "}Production is{" "}
              <span style={{color:"#ef4444"}}>down.</span>
            </h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Error rate spikes. Latency explodes. Phones light up.
              The team scrambles — but Quorum already knows what happened.
            </p>
          </div>

          {/* Story beats */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {STORY_BEATS.map(({phase, label, color, desc}, i) => (
              <div key={label}
                className={`reveal stagger-${i+1} quantum-border rounded-2xl p-6 transition-all duration-500 group cursor-default`}
                style={{
                  background:`linear-gradient(135deg,rgba(0,0,0,0.8),rgba(10,8,30,0.9))`,
                }}>
                <div className="font-mono text-[10px] tracking-[0.3em] mb-3 uppercase" style={{color}}>
                  {phase}
                </div>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 group-hover:scale-110"
                  style={{background:`${color}18`, border:`1px solid ${color}30`}}>
                  {[Activity, Brain, GitBranch, Shield][i] && (() => {
                    const Icon = [Activity, Brain, GitBranch, Shield][i];
                    return <Icon size={15} style={{color}} />;
                  })()}
                </div>
                <h3 className="font-bold text-sm text-white mb-2 tracking-wide">{label}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
                {/* Hover ripple */}
                <div className="mt-4 h-px transition-all duration-500 group-hover:opacity-100 opacity-0"
                  style={{background:`linear-gradient(90deg,transparent,${color},transparent)`}} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TEMPORAL TIMELINE DEMO ──────────────────────────── */}
      <section className="py-32 px-6 relative"
        style={{background:"linear-gradient(180deg,#000008,#050010,#000008)"}}>

        <div className="absolute left-1/2 top-0 -translate-x-1/2 w-px h-32 bg-gradient-to-b from-transparent via-[#6366f1]/40 to-transparent" />

        <div className="max-w-5xl mx-auto">
          <div className="reveal text-center mb-16">
            <div className="font-mono text-xs tracking-[0.4em] text-[#6366f1] mb-4 uppercase">Chapter 02 · The Time Heist</div>
            <h2 className="text-4xl sm:text-5xl font-black mb-4">
              <span className="temporal-gradient">Cognee traverses time.</span>
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              The graph holds every causal chain. Which deployment caused which incident.
              Which commit was the last safe state. Click below to watch the time heist unfold.
            </p>
          </div>
          <div className="reveal">
            <TemporalTimeline />
          </div>
        </div>
      </section>

      {/* ── STATS ───────────────────────────────────────────── */}
      <section className="py-20 px-6 border-y"
        style={{borderColor:"rgba(99,102,241,0.12)", background:"rgba(5,0,16,0.8)"}}>
        <div className="max-w-4xl mx-auto reveal">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              {val:"6s",   label:"Avg detection time"},
              {val:"90%",  label:"MTTR reduction"},
              {val:"19m",  label:"Avg time heist duration"},
              {val:"100%", label:"Human-confirmed rollbacks"},
            ].map(({val, label}) => (
              <div key={label}>
                <div className="text-4xl font-black mb-2 temporal-gradient">{val}</div>
                <div className="text-[11px] uppercase tracking-widest text-slate-500 font-medium">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CHAPTER 03: SAFE STATE RESTORED ────────────────── */}
      <section className="py-32 px-6 relative overflow-hidden">

        <div className="absolute inset-0 pointer-events-none"
          style={{backgroundImage:"radial-gradient(circle at 50% 60%, rgba(16,185,129,0.06) 0%, transparent 65%)"}}>
        </div>

        <div className="max-w-6xl mx-auto">
          <div className="reveal text-center mb-20">
            <div className="font-mono text-xs tracking-[0.4em] text-[#10b981] mb-4 uppercase">Chapter 03 · Safe State Restored</div>
            <h2 className="text-4xl sm:text-5xl font-black mb-4 text-white">
              Everything you need.{" "}
              <span style={{color:"#10b981"}}>Nothing you don&apos;t.</span>
            </h2>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Quorum isn&apos;t just monitoring. It&apos;s memory. Every incident makes the next rollback faster.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(({icon: Icon, title, desc, color}, i) => (
              <div key={title}
                ref={el => { featureRefs.current[i] = el; }}
                className={`reveal tilt stagger-${(i%3)+1} quantum-border rounded-2xl p-7 cursor-default group transition-all duration-300`}
                style={{background:"linear-gradient(135deg,rgba(0,0,8,0.9),rgba(10,8,30,0.95))"}}
                onMouseMove={e => handleTilt(e, i)}
                onMouseEnter={e => {
                  e.currentTarget.style.boxShadow = `0 0 40px ${color}18, 0 0 80px ${color}08`;
                }}
                onMouseLeave={e => {
                  handleTiltLeave(i);
                  e.currentTarget.style.boxShadow = "";
                }}>
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110"
                  style={{background:`${color}15`, border:`1px solid ${color}30`}}>
                  <Icon size={20} style={{color}} />
                </div>
                <h3 className="font-bold text-white mb-3">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
                <div className="mt-5 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{background:`linear-gradient(90deg,${color},transparent)`}} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHY NOT JUST RAG ────────────────────────────────── */}
      <section className="py-28 px-6"
        style={{background:"linear-gradient(180deg,#000008,#050010,#000008)"}}>
        <div className="max-w-4xl mx-auto reveal">
          <div className="quantum-border rounded-3xl p-10 sm:p-16 text-center"
            style={{background:"linear-gradient(135deg,rgba(99,102,241,0.05),rgba(0,0,8,0.98))"}}>
            <div className="font-mono text-xs tracking-[0.4em] text-[#6366f1] mb-6 uppercase">Why not plain vector search?</div>
            <h2 className="text-3xl sm:text-4xl font-black mb-6 text-white">
              RAG finds text.<br />
              <span className="temporal-gradient">Cognee traverses causality.</span>
            </h2>
            <p className="text-slate-400 text-lg mb-12 max-w-2xl mx-auto leading-relaxed">
              The chain{" "}
              <span className="font-mono text-sm" style={{color:"#00d4ff"}}>
                anomaly → incident → root cause → bad deploy → safe state
              </span>{" "}
              is impossible to answer with embeddings alone. You need a graph.
            </p>
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {label:"GRAPH_COMPLETION", desc:"Full causal chain traversal across deployment history", color:"#6366f1"},
                {label:"INSIGHTS",         desc:"Entity relationship extraction — who caused what",      color:"#10b981"},
                {label:"SUMMARIES",        desc:"High-level incident context for fast triage",           color:"#f59e0b"},
              ].map(({label, desc, color})=>(
                <div key={label} className="quantum-border rounded-xl p-5 text-left group hover:scale-[1.02] transition-transform duration-300"
                  style={{background:"rgba(0,0,0,0.6)"}}>
                  <div className="font-mono font-bold text-xs mb-2 tracking-wider" style={{color}}>{label}</div>
                  <div className="text-xs text-slate-500 leading-relaxed">{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ───────────────────────────────────────── */}
      <section className="py-32 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {[1,2,3].map(i=>(
            <div key={i} className="absolute rounded-full border border-[#6366f1]"
              style={{
                width:`${i*280}px`, height:`${i*280}px`,
                opacity:0.06, animation:`timeRipple ${i*1.8+1}s ease-out infinite`,
                animationDelay:`${i*0.6}s`,
              }} />
          ))}
        </div>

        <div className="relative max-w-2xl mx-auto reveal">
          <div className="font-mono text-xs tracking-[0.4em] text-[#10b981] mb-6 uppercase">
            ✦ Timeline restored · System nominal
          </div>
          <h2 className="text-5xl sm:text-6xl font-black mb-6 tracking-tight">
            <span className="temporal-gradient">Your next outage</span><br />
            <span className="text-white">already has a rollback.</span>
          </h2>
          <p className="text-slate-400 text-xl mb-12 leading-relaxed">
            Every incident you survive teaches Quorum. The first time heist takes 31 minutes.
            The tenth takes 6 seconds.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/auth/register"
              className="btn-primary flex items-center gap-3 px-12 py-5 rounded-2xl font-bold text-xl text-white">
              Begin the Time Heist <ArrowRight size={20} />
            </Link>
            <span className="text-xs text-slate-600 font-mono">No credit card · Free forever for small teams</span>
          </div>
        </div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────── */}
      <footer className="py-10 px-6"
        style={{borderTop:"1px solid rgba(99,102,241,0.1)"}}>
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-600 text-sm">
            <Shield size={13} style={{color:"#6366f1"}} />
            <span>Quorum — Powered by <span style={{color:"#6366f1"}}>Cognee</span></span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/auth/login"    className="text-xs text-slate-700 hover:text-slate-400 transition-colors">Sign in</Link>
            <Link href="/auth/register" className="text-xs text-slate-700 hover:text-slate-400 transition-colors">Register</Link>
            <span className="text-slate-800 text-xs font-mono">WeMakeDevs × Cognee Hackathon 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
